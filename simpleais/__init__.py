import calendar
import collections
import gzip
import json
import logging
import os
import re
import time
from functools import reduce
from io import TextIOBase

aivdm_pattern = re.compile(r'([.0-9]+)?\s*(![A-Z]{5},\d,\d,.?,[AB12]?,[^,]+,[0-6]\*[0-9A-F]{2})')


class Bits:
    """
    Integer implementation of bits.
    """

    def __init__(self, *args):
        if len(args) == 2 and isinstance(args[0], int):
            self.length = args[1]
            self.value = args[0]
        elif len(args) == 0:
            self.length = 0
            self.value = 0
        elif len(args) == 1:
            if isinstance(args[0], str):
                self.length = len(args[0])
                self.value = int(args[0], 2)
            elif isinstance(args[0], int):
                self.length = args[0].bit_length()
                if self.length == 0:
                    self.length = 1
                self.value = args[0]
            elif isinstance(args[0], Bits):
                self.length = args[0].length
                self.value = args[0].value
            else:
                raise ValueError("don't know how to parse {}".format(args[0]))
        elif len(args) == 2 and isinstance(args[0], int):
            self.length = args[1]
            self.value = args[0]
        else:
            raise ValueError("don't know how to parse {}, {}".format(args[0], args[1]))

    def __getitem__(self, given):
        if isinstance(given, slice):
            start, stop = given.start, given.stop
            if start > self.length:
                start = self.length
            if stop > self.length:
                stop = self.length
            length = stop - start
            shift = self.length - stop
            value = self.value >> shift & (2 ** length - 1)
            return Bits(value, length)
        elif isinstance(given, int):
            if given > self.length - 1:
                return Bits(0, 0)
            else:
                return self[given:given + 1]
        else:
            raise ValueError("not ready for {}".format(given))

    def __int__(self):
        return self.value

    def __add__(self, other):
        result_value = self.value << other.length | other.value
        result_length = self.length + other.length
        return Bits(result_value, result_length)

    def __str__(self):
        if self.length == 0:
            return ''
        format_string = "{:0" + str(self.length) + "b}"
        return format_string.format(self.value)

    def __repr__(self):
        return "Bits('{}')".format(str(self))

    def __eq__(self, other):
        if isinstance(other, Bits):
            return self.length == other.length and self.value == other.value
        else:
            return int(self) == int(other)

    def __len__(self):
        return self.length

    @classmethod
    def join(cls, array, skip=None, stop=None):
        result_value = 0
        result_length = 0
        for b in array:
            result_value = result_value << b.length | b.value
            result_length += b.length
        if skip:
            result_value = result_value & (2 ** (result_length - skip) - 1)
            result_length = result_length - skip
            stop = stop - skip
        if stop and stop < result_length:
            shift = result_length - stop
            result_value = result_value >> shift
            result_length = result_length - shift
        return Bits(result_value, result_length)


class StreamParser:
    """
    Used to parse live streams of AIS messages.
    """

    def __init__(self, default_to_current_time=False, log_errors=False):
        self.fragment_pool = collections.defaultdict(FragmentPool)
        self.sentence_buffer = collections.deque()
        self.default_to_current_time = default_to_current_time
        self.log_errors = log_errors

    def add(self, message_text):
        thing = parse_one(message_text, self.default_to_current_time)
        if isinstance(thing, Sentence):
            self.sentence_buffer.append(thing)
        elif isinstance(thing, SentenceFragment):
            pool = self.fragment_pool[thing.radio_channel]
            pool.add(thing)
            if pool.has_full_sentence():
                sentence = pool.pop_full_sentence()
                self.sentence_buffer.append(sentence)
        else:
            if self.log_errors:
                logging.getLogger().warn("skipped: \"{}\"".format(message_text.strip()))

    def next_sentence(self):
        return self.sentence_buffer.popleft()

    def has_sentence(self):
        return len(self.sentence_buffer) > 0


def parse_many(messages):
    p = StreamParser()
    result = []
    for m in messages:
        p.add(m)
        if p.has_sentence():
            result.append(p.next_sentence())
    return result


# based on https://en.wikipedia.org/wiki/NMEA_0183
def nmea_checksum(message):
    content = message[1:].split('*')[0]
    result = 0
    for c in content:
        result = result ^ ord(c)
    return result


def parse_one(string, default_to_current_time=False):
    m = aivdm_pattern.search(string)
    if not m:
        return None

    if m.group(1):
        sentence_time = float(m.group(1))
    else:
        if default_to_current_time:
            sentence_time = time.time()
        else:
            sentence_time = None

    message = m.group(2)

    content, checksum = message[1:].split('*')
    fields = content.split(',')
    talker = fields[0][0:2]
    sentence_type = fields[0][2:]
    fragment_count = int(fields[1])
    radio_channel = fields[4]
    payload = NmeaPayload(fields[5], int(fields[6]))
    if fragment_count == 1:
        return Sentence(talker, sentence_type, radio_channel, payload, [checksum], sentence_time, [message])
    else:
        fragment_number = int(fields[2])
        message_id = fields[3]
        return SentenceFragment(talker, sentence_type, fragment_count, fragment_number,
                                message_id, radio_channel, payload, checksum, sentence_time, message)


def parse(message):
    if isinstance(message, list):
        return parse_many(message)
    else:
        return parse_one(message)


class NMEAThing:
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)


def _make_nmea_lookup_tables():
    int_lookup = {}
    bits_lookup = {}
    for val in range(48, 88):
        n = val - 48
        int_lookup[chr(val)] = n
        bits_lookup[chr(val)] = Bits(n, 6)
    for val in range(96, 120):
        n = val - 56
        int_lookup[chr(val)] = n
        bits_lookup[chr(val)] = Bits(n, 6)
    return bits_lookup, int_lookup


_bits_lookup, _int_lookup = _make_nmea_lookup_tables()


class NmeaLump:
    def __init__(self, raw_data, fill_bits=0):
        if not isinstance(raw_data, str):
            raise ValueError("don't like a {}".format(raw_data))
        self.ascii = raw_data
        self.fill = fill_bits
        self._length = 6 * len(self.ascii) - self.fill

    def bit_length(self):
        return self._length

    def int_for_bit_range(self, start, stop):
        if start < 0:
            raise ValueError("Can't go past start for {}:{} of {}".format(start, stop, self))
        if start > self.bit_length() - 1 or stop > self.bit_length():
            raise ValueError("Can't go past end for {}:{} of {}".format(start, stop, self))
        start_char = start // 6
        stop_char = 1 + (stop - 1) // 6
        result = 0
        length = 0
        for c in self.ascii[start_char:stop_char]:
            result = result << 6
            length += 6
            result = result | _int_lookup[c]
        shift = start_char * 6
        front_trim = start - shift
        if front_trim > 0:
            length -= front_trim
            result = result & (2 ** length - 1)
        end_trim = length - (stop - start)
        if end_trim > 0:
            length -= end_trim
            result = result >> end_trim

        return result

    def bit_range(self, start, stop):
        if start < 0:
            raise ValueError("Can't go past start for {}:{} of {}".format(start, stop, self))
        if start > self.bit_length() - 1 or stop > self.bit_length():
            raise ValueError("Can't go past end for {}:{} of {}".format(start, stop, self))
        start_char = start // 6
        stop_char = 1 + (stop - 1) // 6
        chars = self.ascii[start_char:stop_char]
        shift = start_char * 6
        result = self._bits_for(chars, start - shift, stop - shift)
        return result

    def bits(self):
        return self.bit_range(0, self.bit_length())

    @staticmethod
    def _bits_for(ascii_representation, start, stop):
        if len(ascii_representation) == 0:
            return Bits()
        elif len(ascii_representation) == 1 and start == 0 and stop == 6:
            return _bits_lookup[ascii_representation[0]]

        bit_lumps = [_bits_lookup[c] for c in ascii_representation]
        return Bits.join(bit_lumps, start, stop)

    def __repr__(self, *args, **kwargs):
        return "NmeaLump('{}', {})".format(self.ascii, self.fill)


# noinspection PyCallingNonCallable
class NmeaPayload:
    """
    Represents the heart of an AIS message plus related decoding.
    """

    def __init__(self, raw_data, fill_bits=0):
        if isinstance(raw_data, Bits):
            raise NotImplementedError
        elif isinstance(raw_data, Bits):
            self.data = raw_data
        elif isinstance(raw_data, str):
            self.data = [NmeaLump(raw_data, fill_bits)]
        elif isinstance(raw_data, list) and isinstance(raw_data[0], NmeaLump):
            self.data = raw_data
        else:
            raise ValueError("Don't like a {}".format(raw_data))

    def unsigned_int(self, start, end):
        return int(self._bit_range(start, end))

    @property
    def bits(self):
        return Bits.join([l.bits() for l in self.data])

    @staticmethod
    def _bits_for(ascii_representation, fill_bits):
        result = []
        for pos in range(0, len(ascii_representation) - 1):
            result.append(_bits_lookup[ascii_representation[pos]])
        bits_at_end = 6 - fill_bits
        selected_bits = _bits_lookup[ascii_representation[-1]][0:bits_at_end]
        result.append(selected_bits)
        return Bits.join(result)

    def __len__(self):
        return self.bit_length()

    def bit_length(self):
        return sum([l.bit_length() for l in self.data])

    @classmethod
    def join(cls, items):
        l = []
        for p in items:
            l.extend(p.data)
        return NmeaPayload(l)

    def has_bits(self, start, stop):
        return start >= 0 and stop < self.bit_length()

    def int_for_bit_range(self, start, stop):
        # Can we pull from the first lump?
        if stop <= self.data[0].bit_length():
            return self.data[0].int_for_bit_range(start, stop)

        # most ints are in the first lump, so ignore other complexity for now
        return int(self._bit_range(start, stop))

    def _twos_comp(self, val, length):
        if (val & (1 << (length - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
            val = val - (1 << length)  # compute negative value
        return val

    def scaled_int_for_bit_range(self, start, stop, scale):
        out = self._twos_comp(self.int_for_bit_range(start, stop), stop - start)
        return round(out / 60 / (10 ** scale), 4)

    def text_for_bit_range(self, start, stop):
        bits = self._bit_range(start, stop)

        def chunks(s, n):
            for i in range(0, len(s), n):
                yield s[i:i + n]

        raw_ints = [int(nibble) for nibble in chunks(bits, 6)]
        mapped_ints = [i if i > 31 else i + 64 for i in raw_ints]
        text = ''.join([chr(i) for i in mapped_ints]).strip()
        text = text.rstrip('@').strip()
        return text

    def _bit_range(self, start, stop):
        # Can we pull from the first lump?
        if stop <= self.data[0].bit_length():
            return self.data[0].bit_range(start, stop)
        # Can we pull from any single lump?
        result = self._quick_bit_range(start, stop)
        if result:
            return result
        # Damn. Convert it all to bits. // TODO: make faster?
        return self._full_bit_range(start, stop)

    def _quick_bit_range(self, start, stop):
        pos = 0
        offset = 0
        end = len(self.data)
        while pos < end:
            lump = self.data[pos]
            if offset <= start and stop <= offset + lump.bit_length():
                return lump.bit_range(start - offset, stop - offset)
            else:
                offset += lump.bit_length()
                pos += 1
        return None

    def _full_bit_range(self, start, stop):
        return Bits.join([l.bits() for l in self.data])[start:stop]

    def __repr__(self):
        return "NmeaPayload({})".format(self.data.__repr__())


class FieldDecoder:
    name = 'unknown'
    description = "Unknown field"

    def bits(self, sentence):
        raise NotImplementedError

    def decode(self, sentence):
        raise NotImplementedError

    def valid(self, sentence):
        raise NotImplementedError


class BitFieldDecoder(FieldDecoder):
    def __init__(self, name, start, end, data_type, description):
        self.name = name
        self.start = start
        self.end = end
        self.length = 1 + end - start
        self.bit_range = slice(start, end + 1)
        self.description = description
        self._nmea_decode = self._appropriate_nmea_decoder(data_type, name)
        self.short_bits_ok = data_type in ['s', 't', 'd']  # if we get partial text or data, that's better than nothing

    def __repr__(self, *args, **kwargs):
        return "FieldDecoder({}, {}, {}, {})".format(self.name, self.description, self.start, self.end)

    def _appropriate_nmea_decoder(self, data_type, name):
        if name == 'mmsi':
            return self._parse_mmsi
        elif name == 'lon' and data_type == 'I4':
            return self._parse_lon
        elif name == 'lat' and data_type == 'I4':
            return self._parse_lat
        elif name == 'lon' and data_type == 'I1':
            return lambda b: None  # Type 17 is weird; ignore for now
        elif name == 'lat' and data_type == 'I1':
            return lambda b: None  # Type 17 is weird; ignore for now
        elif data_type == 't' or data_type == 's':
            return self._parse_text
        elif data_type == 'I1':
            return lambda p: self.scaled_int(p, 1)
        elif data_type == 'I3':
            return lambda p: self.scaled_int(p, 3)
        elif data_type == 'I4':
            return lambda p: self.scaled_int(p, 4)
        elif data_type == 'u':
            return self.int
        elif data_type == 'U1':
            return lambda p: self.int(p) / 10.0
        elif data_type == 'd':
            return lambda p: p.bits[self.start:self.end + 1]
        elif data_type == 'e':
            def lookup(p):
                i = self.int(p)
                if i not in ENUM_LOOKUPS[name]:
                    ENUM_LOOKUPS[name][i] = AisEnum(i, "enum-unknown-{}".format(i))
                return ENUM_LOOKUPS[name][i]

            if name == 'shiptype':
                return lookup
            else:
                return lambda p: "enum-{}".format(self.int(p))  # TODO: find and include enumerated types
        elif data_type == 'b':
            return lambda p: self.int(p) == 1
        elif data_type == 'x':
            return self.int

    def int(self, payload):
        return payload.int_for_bit_range(self.start, self.end + 1)

    def scaled_int(self, payload, scale):
        return payload.scaled_int_for_bit_range(self.start, self.end + 1, scale)

    def _appropriate_bit_decoder(self, data_type, name):
        raise ValueError("Sorry, don't know how to parse '{}' for field '{}' yet".format(data_type, self.name))

    def decode(self, sentence):
        return self._nmea_decode(sentence.payload)

    def bits(self, sentence):
        return sentence.message_bits()[self.bit_range]

    def valid(self, sentence):
        return len(sentence.message_bits()) > self.end

    def _parse_mmsi(self, payload):
        return "%09i" % payload.int_for_bit_range(self.start, self.end + 1)

    def _parse_lon(self, payload):
        if not payload.has_bits(self.start, self.end + 1):
            return None
        result = payload.scaled_int_for_bit_range(self.start, self.end + 1, 4)
        if result is not None and result != 181.0 and -180.0 <= result <= 180.0:
            return result

    def _parse_lat(self, payload):
        if not payload.has_bits(self.start, self.end + 1):
            return None
        result = payload.scaled_int_for_bit_range(self.start, self.end + 1, 4)
        if result is not None and result != 91.0 and -90.0 <= result <= 90.0:
            return result

    def _parse_text(self, payload):
        return payload.text_for_bit_range(self.start, self.end + 1)


class TimeFieldDecoder(FieldDecoder):
    name = 'time'
    description = "UTC Time Reference"

    def decode(self, sentence):
        if self.we_have_the_fields(sentence) and self.the_fields_are_ok(sentence):
            return calendar.timegm((sentence['year'], sentence['month'],
                                    sentence['day'], sentence['hour'],
                                    sentence['minute'], sentence['second']))

    def we_have_the_fields(self, sentence):
        return 1980 <= sentence['year'] <= 9999 and \
               1 <= sentence['month'] <= 12 and \
               1 <= sentence['day'] <= 31 and \
               0 <= sentence['hour'] <= 24 and \
               0 <= sentence['minute'] <= 59 and \
               0 <= sentence['second'] <= 59

    def the_fields_are_ok(self, sentence):
        return all(name in sentence for name in ['year', 'month', 'day', 'hour', 'minute', 'second'])

    def bits(self, sentence):
        return sentence.message_bits()[
               self._first_field(sentence).decoder.start:self._last_field(sentence).decoder.end + 1]

    def valid(self, sentence):
        return self._first_field(sentence).valid() and self._last_field(sentence).valid()

    def _last_field(self, sentence):
        return sentence.field('second')

    def _first_field(self, sentence):
        return sentence.field('year')


class MessageDecoder:
    def __init__(self, message_info):
        self.field_decoders = []
        self.field_decoders_by_id = collections.OrderedDict()
        for field in message_info['fields']:
            decoder = BitFieldDecoder(field['member'], field['start'], field['end'], field['type'],
                                      field['description'])
            self.add_field_decoder(field['member'], decoder)

    def add_field_decoder(self, name, decoder):
        self.field_decoders.append(decoder)
        self.field_decoders_by_id[name] = decoder

    def bit_range(self, name):
        return self.field_decoders_by_id[name].bit_range

    def decode(self, name, sentence):
        if name in self.field_decoders_by_id:
            return self.field_decoders_by_id[name].decode(sentence)

    def __contains__(self, name):
        return name in self.field_decoders_by_id

    def fields(self):
        return self.field_decoders_by_id.values()

    def field(self, key):
        if isinstance(key, int):
            return self.field_decoders[key]
        else:
            return self.field_decoders_by_id[key]


class AisEnum:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __int__(self):
        return self.key

    def __str__(self):
        return self.value

    def __repr__(self):
        return 'AisEnum({}, {})'.format(self.key, self.value)


def as_enum(key, value):
    return AisEnum(key, value)


def as_enums(json_dict):
    result = {}
    for k in json_dict:
        result[int(k)] = as_enum(int(k), json_dict[k])
    return result


def _load_decoders(source_file):
    loaded_json = json.loads(open(os.path.join(os.path.dirname(__file__), source_file)).read())
    message_type_json = loaded_json['messages']
    message_result = {}
    for message_type_id in range(1, 28):
        message_result[message_type_id] = MessageDecoder(message_type_json[str(message_type_id)])

    # add derived fields
    message_result[4].add_field_decoder('time', TimeFieldDecoder())

    enum_result = {'shiptype': as_enums(loaded_json['lookups']['ship_type'])}
    return message_result, enum_result


MESSAGE_DECODERS, ENUM_LOOKUPS = _load_decoders('aivdm.json')

BACKUP_DECODER = MessageDecoder({
    "name": "Unknown message",
    "fields": [
        {
            "start": 0,
            "end": 5,
            "description": "Message Type",
            "member": "type",
            "type": "u"
        },
        {
            "start": 6,
            "end": 7,
            "description": "Repeat Indicator",
            "member": "repeat",
            "type": "u"
        },
        {
            "start": 8,
            "end": 37,
            "description": "MMSI",
            "member": "mmsi",
            "type": "u"
        },
        {
            "start": 38,
            "end": 1000,
            "description": "Payload",
            "member": "payload",
            "type": "d"
        }
    ]
}
)


def _decoder_for_type(number):
    if number in MESSAGE_DECODERS:
        return MESSAGE_DECODERS[number]
    else:
        return BACKUP_DECODER


class SentenceFragment:
    def __init__(self, talker, sentence_type, total_fragments, fragment_number, message_id, radio_channel, payload,
                 checksum, received_time=None, text=None):
        self.talker = talker
        self.sentence_type = sentence_type
        self.total_fragments = total_fragments
        self.fragment_number = fragment_number
        self.message_id = message_id
        self.radio_channel = radio_channel
        self.payload = payload
        self.checksum = checksum
        self.time = received_time
        self.text = text

    def initial(self):
        return self.fragment_number == 1

    def last(self):
        return self.fragment_number == self.total_fragments

    def key(self):
        key = (self.talker, self.sentence_type, self.total_fragments, self.message_id, self.radio_channel)
        return key

    def follows(self, other):
        return (self.fragment_number == other.fragment_number + 1) and self.key() == other.key()

    def bits(self):
        return self.payload.bits

    def check(self):
        return int(self.checksum, 16) == nmea_checksum(self.text)


class Field(object):
    # You would think that a Sentence would be composed of these, but 99% of usage doesn't
    # require this level of introspection, so we avoid creating a bunch of useless objects
    # and mainly think of sentences as a lump of bits.
    def __init__(self, field_decoder, sentence):
        self.decoder = field_decoder
        self.sentence = sentence

    def name(self):
        return self.decoder.name

    def description(self):
        return self.decoder.description

    def value(self):
        return self.decoder.decode(self.sentence)

    def bits(self):
        return self.decoder.bits(self.sentence)

    def valid(self):
        return self.decoder.valid(self.sentence)


class Sentence:
    def __init__(self, talker, sentence_type, radio_channel, payload, checksums, received_time=None, text=None):
        self.talker = talker
        self.sentence_type = sentence_type
        self.radio_channel = radio_channel
        self.payload = payload
        self.checksums = checksums
        self.time = received_time
        self.text = text
        self.type_num = _int_lookup[payload.data[0].ascii[0]]
        self._decoder = _decoder_for_type(self.type_num)

    def type_id(self):
        return self.type_num

    def check(self):
        checks = self.fragment_checksum_validity()
        return reduce(lambda a, b: a and b, checks)

    def fragment_checksum_validity(self):
        return [nmea_checksum(t) == int(c, 16) for t, c in (zip(self.text, self.checksums))]

    def location(self):
        lon = self['lon']
        lat = self['lat']
        if lon and lat:
            return lon, lat

    def message_bits(self):
        return self.payload.bits

    def __getitem__(self, item):
        return self._decoder.decode(item, self)

    def __contains__(self, item):
        return item in self._decoder and self.__getitem__(item) is not None

    def field(self, key):
        return Field(self._decoder.field(key), self)

    def fields(self):
        return [Field(fd, self) for fd in self._decoder.fields()]

    @classmethod
    def from_fragments(cls, matching_fragments):
        first = matching_fragments[0]
        text = [f.text for f in matching_fragments]
        checksums = [f.checksum for f in matching_fragments]
        return Sentence(first.talker, first.sentence_type, first.radio_channel,
                        NmeaPayload.join([f.payload for f in matching_fragments]),
                        checksums, first.time, text)

    def __repr__(self):
        return "Sentence({}, {})".format(self.time, self.text)

    def __str__(self):
        return "Sentence(type {}, from {}, at {})".format(self.type_num, self['mmsi'], self.time)


class FragmentPool:
    """
    A smart holder for SentenceFragments that can tell when a valid message has been found.
    Unlike TCP fragments, AIS fragments arrive in order and soon, so this can be aggressive
    in discarding odd socks.
    """

    def __init__(self):
        self.fragments = []
        self.full_sentence = None

    def has_full_sentence(self):
        return self.full_sentence is not None

    def pop_full_sentence(self):
        if not self.full_sentence:
            raise ValueError
        result = self.full_sentence
        self.full_sentence = None
        return result

    def _has_complete_fragment_set(self):
        actual = sorted([f.fragment_number for f in self.fragments])
        expected = list(range(1, self.fragments[0].total_fragments + 1))
        return actual == expected

    def add(self, fragment):
        if len(self.fragments) > 0 and not fragment.follows(self.fragments[-1]):
            self.fragments.clear()

        self.fragments.append(fragment)

        if fragment.last() and self._has_complete_fragment_set():
            self.full_sentence = Sentence.from_fragments(self.fragments)
            self.fragments.clear()


def lines_from_source(source):
    if isinstance(source, TextIOBase):
        for line in source:
            yield line
    elif re.match("/dev/tty.*", source):
        yield from _handle_serial_source(source)
    elif re.match("https?://.*", source):
        yield from _handle_url_source(source)
    else:
        # assume it's a file
        yield from _handle_file_source(source)


def fragments_from_source(source, log_errors=False):
    for line in lines_from_source(source):
        # noinspection PyBroadException
        try:
            m = aivdm_pattern.search(line)
            if m:
                yield m.group(0)
            elif log_errors:
                logging.getLogger().warn("skipped: \"{}\"".format(line.strip()))
        except Exception:
            logging.getLogger().error("unexpected failure for line {} in source {}".format(line, source), exc_info=True)


def sentences_from_source(source, log_errors=False):
    parser = StreamParser(log_errors=log_errors)
    for fragment in lines_from_source(source):
        # noinspection PyBroadException
        try:
            parser.add(fragment)
            if parser.has_sentence():
                yield parser.next_sentence()
        except Exception:
            logging.getLogger().error("unexpected failure for fragment {} in source {}".format(fragment, source),
                                      exc_info=True)


# noinspection PyBroadException
def _handle_serial_source(source):
    import serial

    while True:
        # noinspection PyBroadException
        try:
            with serial.Serial(source, 38400, timeout=10) as f:
                while True:
                    raw_line = f.readline()
                    try:
                        yield raw_line.decode('ascii')
                    except Exception:
                        logging.getLogger().warn("Failure for input: \"{}\"".format(raw_line.strip()), exc_info=True)
        except Exception:
            logging.getLogger().error("unexpected failure", exc_info=True)
            time.sleep(1)


def _handle_url_source(source):
    import urllib.request

    while True:
        # noinspection PyBroadException
        try:
            # noinspection PyUnresolvedReferences
            with urllib.request.urlopen(source) as f:
                for line in f:
                    yield line.decode('utf-8')
        except Exception:
            logging.getLogger().error("unexpected failure in source {}".format(source), exc_info=True)
            time.sleep(1)


def _handle_file_source(source):
    if source.endswith('.gz'):
        source_reader = gzip.open(source, mode='rt')
    else:
        source_reader = open(source)
    with source_reader as f:
        for line in f:
            yield line
