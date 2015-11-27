import collections
from functools import reduce

from BitVector import BitVector


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
    for ascii in range(48, 88):
        # noinspection PyCallingNonCallable
        lookup[chr(ascii)] = BitVector(size=6, intVal=ascii - 48)
    for ascii in range(96, 120):
        # noinspection PyCallingNonCallable
        lookup[chr(ascii)] = BitVector(size=6, intVal=ascii - 56)
    return lookup


_nmea_lookup = _make_nmea_lookup_table()


class NmeaPayload:
    def __init__(self, ascii_representation, fill_bits):
        child_vectors = [_nmea_lookup[c] for c in ascii_representation]
        if fill_bits:
            child_vectors[-1] = child_vectors[-1][0:(6 - fill_bits)]
        self.bits = reduce(lambda x, y: x + y, child_vectors)

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

    def message_type(self):
        return int(self.payload.bits[0:6])


# TODO: this needs to understand message guts. Perhaps it should be a static method on Sentence.
def merge_matching_fragments(matching_fragments):
    first = matching_fragments[0]
    return Sentence(first.talker, first.sentence_type, first.radio_channel, first.payload)


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
                self.full_sentence = merge_matching_fragments(matches)
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
