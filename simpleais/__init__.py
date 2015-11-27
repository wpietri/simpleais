import collections


def parse_many(messages):
    first_pass = collections.deque()
    for m in messages:
        first_pass.append(parse_one(m))

    result = []
    fragment_pool = FragmentPool()
    while len(first_pass)>0:
        m = first_pass.popleft()
        if not m.partial():
            result.append(m)
        else:
            fragment_pool.add(m)
            if fragment_pool.has_full_sentence():
                result.append(fragment_pool.pop_full_sentence())

    return result



def parse_one(message):
    if message == '':
        return None

    result = {}
    fields = message.split(',')

    result['talker'] = fields[0][1:3]
    result['sentence_type'] = fields[0][3:]
    fragment_count = int(fields[1])
    print(fragment_count)
    if fragment_count == 1:
        return Sentence(Talker(fields[0][1:3]), SentenceType(fields[0][3:]))
    else:
        return SentenceFragment(Talker(fields[0][1:3]), SentenceType(fields[0][3:]), int(fields[1]), int(fields[2]), int(fields[3]))



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

class SentenceFragment:
    def __init__(self,talker, sentence_type, total_fragments, fragment_number, message_id):
        self.talker = talker
        self.sentence_type = sentence_type
        self.total_fragments = total_fragments
        self.fragment_number = fragment_number
        self.message_id = message_id

    def initial(self):
        return self.fragment_number == 1
    def key(self):
        return (self.talker, self.sentence_type, self.total_fragments, self.message_id)
    def partial(self):
        return True

class Sentence:
    def __init__(self,talker, sentence_type):
        self.talker = talker
        self.sentence_type = sentence_type

    def partial(self):
        return False

# TODO: this needs to understand message guts. Perhaps it should be a static method on Sentence.
def merge_matching_fragments(matching_fragments):
    first = matching_fragments[0]
    return Sentence(first.talker, first.sentence_type)


class FragmentPool:
    """
    A smart holder for SentenceFragments that can tell when
    a valid message has been found.
    """

    def __init__(self):
        self.fragments = []
        self.full_sentence = None

    def has_full_sentence(self):
        if self.full_sentence == None:
            self.seek_full_sentence()
        return not self.full_sentence == None

    def seek_full_sentence(self):
        initials = [f for f in self.fragments if f.initial()]
        for initial in initials:
            key = initial.key()
            matches = [f for f in self.fragments if f.key()==key]
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

