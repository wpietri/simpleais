import collections
from functools import reduce
import logging
import re
from time import sleep

aivdm_pattern = re.compile(r'\![A-Z]{5},\d,\d,.?,[AB12],[^,]+,[0-5]\*[0-9A-F]{2}')


class Bits:
    def __init__(self, *args, **kwargs):
        if len(args)==0:
            self.contents = ""
        elif len(args)==1:
            if isinstance(args[0], str):
                self.contents = args[0]
            elif isinstance(args[0], int):
                self.contents = "{:b}".format(args[0])
            else:
                raise ValueError("don't know how to parse {}".format(args[0]))
        elif len(args)==2 and isinstance(args[0], int):
            format = "{:0" + str(args[1]) + "b}"
            self.contents = format.format(args[0])
        else:
            raise ValueError("don't know how to parse {}, {}".format(args[0], args[1]))


    def append(self, other):
        if not isinstance(other, Bits):
            raise ValueError
        self.contents += other.contents

    def __int__(self):
        return int(self.contents, 2)

    def __getitem__(self, given):
        return Bits(self.contents.__getitem__(given))

    def __add__(self, other):
        return Bits(self.contents + other.contents)

    def __len__(self):
        return self.contents.__len__()

    def __eq__(self, other):
        return self.contents.__eq__(other.contents)

    @classmethod
    def join(cls, array):
        return Bits(''.join(b.contents for b in array))


class StreamParser:
    """
    Used to parse live streams of AIS messages.
    """

    def __init__(self):
        self.fragment_pool = {'A': FragmentPool(), 'B': FragmentPool()}
        self.sentence_buffer = collections.deque()

    def add(self, message_text):
        thing = parse_one(message_text)
        if isinstance(thing, Sentence):
            self.sentence_buffer.append(thing)
        elif isinstance(thing, SentenceFragment):
            pool = self.fragment_pool[thing.radio_channel]
            pool.add(thing)
            if pool.has_full_sentence():
                sentence = pool.pop_full_sentence()
                self.sentence_buffer.append(sentence)

    def nextSentence(self):
        return self.sentence_buffer.popleft()

    def hasSentence(self):
        return len(self.sentence_buffer) > 0


def parse_many(messages):
    p = StreamParser()
    result = []
    for m in messages:
        p.add(m)
        if p.hasSentence():
            result.append(p.nextSentence())
    return result


def parse_one(message):
    if message == '':
        return None

    content, checksum = message[1:].split('*')
    fields = content.split(',')
    talker = Talker(fields[0][0:2])
    sentence_type = SentenceType(fields[0][2:])
    fragment_count = int(fields[1])
    radio_channel = fields[4]
    payload = NmeaPayload(fields[5], int(fields[6]))

    if fragment_count == 1:
        return Sentence(talker, sentence_type, radio_channel, payload)
    else:
        fragment_number = int(fields[2])
        message_id = int(fields[3])
        return SentenceFragment(talker, sentence_type, fragment_count, fragment_number,
                                message_id, radio_channel, payload)


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
        return (isinstance(other, self.__class__)
                and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)


class Talker(NMEAThing):
    pass


class SentenceType(NMEAThing):
    pass


def _make_nmea_lookup_table():
    lookup = {}
    for val in range(48, 88):
        lookup[chr(val)] = Bits(val - 48, 6)
    for val in range(96, 120):
        lookup[chr(val)] = Bits(val - 56, 6)
    return lookup


_nmea_lookup = _make_nmea_lookup_table()


# noinspection PyCallingNonCallable
class NmeaPayload:
    """
    Represents the decoded heart of an AIS message. The BitVector class used
    is not very fast and a bit rough, but is adequate for now. If performance
    becomes an issue, it might be worth replacing. See
    http://stackoverflow.com/questions/20845686/python-bit-array-performant
    for options.
    """

    def __init__(self, raw_data, fill_bits=0):
        if isinstance(raw_data, Bits):
            self.bits = raw_data
        else:
            self.bits = self._bits_for(raw_data, fill_bits)

    @staticmethod
    def _bits_for(ascii_representation, fill_bits):
        buf = []
        for pos in range(0, len(ascii_representation) - 1):
            buf.append(_nmea_lookup[ascii_representation[pos]])
        bits_at_end = 6 - fill_bits
        selected_bits = _nmea_lookup[ascii_representation[-1]][0:bits_at_end]
        buf.append(selected_bits)
        return Bits.join(buf)

    def __len__(self):
        return len(self.bits)


class SentenceFragment:
    def __init__(self, talker, sentence_type, total_fragments, fragment_number, message_id, radio_channel, payload):
        self.talker = talker
        self.sentence_type = sentence_type
        self.total_fragments = total_fragments
        self.fragment_number = fragment_number
        self.message_id = message_id
        self.radio_channel = radio_channel
        self.payload = payload

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


class Sentence:
    def __init__(self, talker, sentence_type, radio_channel, payload):
        self.talker = talker
        self.sentence_type = sentence_type
        self.radio_channel = radio_channel
        self.payload = payload

    def type_id(self):
        return int(self.payload.bits[0:6])

    def message_bits(self):
        return self.payload.bits

    @classmethod
    def from_fragments(cls, matching_fragments):
        first = matching_fragments[0]
        message_bits = reduce(lambda a, b: a + b, [f.bits() for f in matching_fragments])
        return Sentence(first.talker, first.sentence_type, first.radio_channel, NmeaPayload(message_bits))

    def __getitem__(self, item):
        bits = self.payload.bits
        if self.type_id() in [1, 2, 3]:
            if item == 'mmsi':
                return self._parse_mmsi(bits[8:38])
            if item == 'lat':
                return self._parse_latlong(bits[89:116])
            if item == 'lon':
                return self._parse_latlong(bits[61:89])
        if self.type_id() == 5:
            if item == 'mmsi':
                return self._parse_mmsi(bits[8:38])
            if item == 'shipname':
                return self._parse_text(bits[112:232])
            if item == 'destination':
                return self._parse_text(bits[302:422])

    def _parse_mmsi(self, bits):
        return "%09i" % int(bits)

    def _parse_latlong(self, bits):
        def twos_comp(val, bits):
            if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
                val = val - (1 << bits)  # compute negative value
            return val

        out = twos_comp(int(bits), len(bits))
        result = float("%.4f" % (out / 60.0 / 10000.0))
        return result

    def _parse_text(self, bits):
        def chunks(s, n):
            for i in range(0, len(s), n):
                yield s[i:i + n]

        raw_ints = [int(nibble) for nibble in chunks(bits, 6)]
        mapped_ints = [i if i > 31 else i + 64 for i in raw_ints]
        text = ''.join([chr(i) for i in mapped_ints]).strip()
        text = text.rstrip('@').strip()
        return text


class FragmentPool:
    """
    A smart holder for SentenceFragments that can tell when
    a valid message has been found.
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

    def add(self, fragment):
        if len(self.fragments) > 0 and not fragment.follows(self.fragments[-1]):
            self.fragments.clear()
        self.fragments.append(fragment)
        if fragment.last():
            self.full_sentence = Sentence.from_fragments(self.fragments)
            self.fragments.clear()


def lines_from_source(source):
    if re.match("/dev/tty.*", source):
        yield from _handle_serial_source(source)
    elif re.match("https?://.*", source):
        yield from _handle_url_source(source)
    else:
        # assume it's a file
        yield from _handle_file_source(source)


def fragments_from_source(source):
    for line in lines_from_source(source):
        try:
            m = aivdm_pattern.search(line)
            if m:
                yield m.group(0)
            else:
                logging.getLogger().warn("skipped: \"{}\"".format(line.strip()))
        except Exception as e:
            print("failure", e, "for", line)


def sentences_from_source(source):
    parser = StreamParser()
    for fragment in fragments_from_source(source):
        try:
            parser.add(fragment)
            if parser.hasSentence():
                yield parser.nextSentence()
        except Exception as e:
            print("failure", e, "for", fragment)


def _handle_serial_source(source):
    import serial

    while True:
        try:
            with serial.Serial(source, 38400, timeout=10) as f:
                while True:
                    raw_line = f.readline()
                    try:
                        yield raw_line.decode('ascii')
                    except:
                        print("weird input", raw_line)
        except Exception as e:
            print("unexpected failure", e)
            sleep(1)


def _handle_url_source(source):
    import urllib.request

    while True:
        try:
            with urllib.request.urlopen(source) as f:
                for line in f:
                    yield line.decode('utf-8')
        except Exception as e:
            print("unexpected failure", e)
            sleep(1)


def _handle_file_source(source):
    with open(source) as f:
        for line in f:
            yield line
