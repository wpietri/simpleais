from collections import defaultdict
import time

from simpleais import lines_from_source, sentences_from_source


class Timer:
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.duration = self.end - self.start


class Counter:
    def __init__(self):
        self.counts = defaultdict(int)

    def countChars(self, string):
        for char in string:
            self.count(char)

    def count(self, thingy):
        self.counts[thingy] += 1


counter = Counter()
filename = 'sample.ais'


def fake_thing():
    global t1
    with Timer() as t1:
        for line in lines_from_source(filename):
            counter.countChars(line)


fake_thing()

print("comparison load takes", t1.duration)


def real_thing():
    global t2
    with Timer() as t2:
        for sentence in sentences_from_source(filename):
            counter.count(sentence['mmsi'])


real_thing()

print("actual load takes    ", t2.duration)

print()
print("expected ratio is ~2")
print("actual ratio is   ", t2.duration / t1.duration)
