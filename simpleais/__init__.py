import collections
from functools import reduce

from bitstring import BitArray, Bits


class StreamParser:
    """
    Used to parse live streams of AIS messages.
    """

    def __init__(self):
        self.fragment_pool = FragmentPool()
        self.sentence_buffer=collections.deque()


    def add(self, message_text):
        thing = parse_one(message_text)
        if isinstance(thing, Sentence):
            self.sentence_buffer.append(thing)
        elif isinstance(thing, SentenceFragment):
            self.fragment_pool.add(thing)
            if self.fragment_pool.has_full_sentence():
                sentence = self.fragment_pool.pop_full_sentence()
                self.sentence_buffer.append(sentence)


    def nextSentence(self):
        return self.sentence_buffer.popleft()

    def hasSentence(self):
        return len(self.sentence_buffer)>0


def parse_many(messages):
    first_pass = collections.deque()
    for m in messages:
        first_pass.append(parse_one(m))

    result = []
    fragment_pool = FragmentPool()
    while len(first_pass) > 0:
        m = first_pass.popleft()
        if isinstance(m, Sentence):
            result.append(m)
        else:
            fragment_pool.add(m)
            if fragment_pool.has_full_sentence():
                result.append(fragment_pool.pop_full_sentence())

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
        lookup[chr(val)] = Bits(uint=val - 48, length=6)
    for val in range(96, 120):
        lookup[chr(val)] = Bits(uint=val - 56, length=6)
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
        bits = BitArray(None)
        for c in range(0, len(ascii_representation) - 1):
            bits.append(_nmea_lookup[ascii_representation[c]])
        bits_at_end = 6 - fill_bits
        selected_bits = _nmea_lookup[ascii_representation[-1]][0:bits_at_end]
        bits.append(selected_bits)
        return bits

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

    def key(self):
        key = (self.talker, self.sentence_type, self.total_fragments, self.message_id)
        return key

    def bits(self):
        return self.payload.bits


class Sentence:
    def __init__(self, talker, sentence_type, radio_channel, payload):
        self.talker = talker
        self.sentence_type = sentence_type
        self.radio_channel = radio_channel
        self.payload = payload

    def type_id(self):
        return self.payload.bits[0:6].uint

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
                return self.mmsi(bits[8:38])
            if item == 'lat':
                return self.latlong(bits[89:116])
            if item == 'lon':
                return self.latlong(bits[61:89])
        if self.type_id() == 5:
            if item == 'mmsi':
                return self.mmsi(bits[8:38])
            if item == 'shipname':
                return self.text(bits[112:232])
            if item == 'destination':
                return self.text(bits[302:422])

    def mmsi(self, bits):
        return "%09i" % bits.uint

    def latlong(self, bits):
        return float("%.4f" % (bits.int / 60.0 / 10000.0))

    def text(self, bits):
        raw_ints = [nibble.uint for nibble in bits.cut(6)]
        mapped_ints = [i if i > 31 else i + 64 for i in raw_ints]
        return ''.join([chr(i) for i in mapped_ints]).strip()


class FragmentPool:
    """
    A smart holder for SentenceFragments that can tell when
    a valid message has been found.
    """

    def __init__(self):
        self.fragments = []
        self.full_sentence = None

    def has_full_sentence(self):
        if self.full_sentence is None:
            self._seek_full_sentence()
        return self.full_sentence is not None

    def _seek_full_sentence(self):
        initials = [f for f in self.fragments if f.initial()]
        for initial in initials:
            key = initial.key()
            matches = [f for f in self.fragments if f.key() == key]
            if len(matches) >= initial.total_fragments:
                self.full_sentence = Sentence.from_fragments(matches)
                for match in matches:
                    self.fragments.remove(match)

            return

    def pop_full_sentence(self):
        if not self.full_sentence:
            raise ValueError
        result = self.full_sentence
        self.full_sentence = None
        return result

    def add(self, fragment):
        self.fragments.append(fragment)
