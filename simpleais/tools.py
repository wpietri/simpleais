from collections import defaultdict
import os
import sys

import click

from . import sentences_from_source


def print_sentence_source(text, file=sys.stdout):
    if isinstance(text, str):
        print(text, file=file)
    else:
        for line in text:
            print(line, file=file)


def sentences_from_sources(sources):
    if len(sources) > 0:
        for source in sources:
            for sentence in sentences_from_source(source):
                yield sentence
    else:
        for sentence in sentences_from_source(sys.stdin):
            yield sentence


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--mmsi', '-m', multiple=True)
@click.option('--mmsi-file', '-f')
def grep(sources, mmsi, mmsi_file=None):
    if mmsi_file:
        mmsi = list(mmsi)
        with open(mmsi_file, "r") as f:
            mmsi.extend([l.strip() for l in f.readlines()])
        mmsi = frozenset(mmsi)
    for sentence in sentences_from_sources(sources):
        if len(mmsi) > 0:
            if sentence['mmsi'] in mmsi:
                print_sentence_source(sentence.text)
        else:
            print_sentence_source(sentence.text)


@click.command()
@click.argument('sources', nargs=-1)
def as_text(sources):
    for sentence in sentences_from_sources(sources):
        print("{} {:2} {:10}".format(sentence.time, sentence.type_id(), str(sentence['mmsi'])))


@click.command()
@click.argument('source', nargs=1)
@click.argument('dest', nargs=1, required=False)
def burst(source, dest):
    if not dest:
        dest = source
    writers = {}
    fname, ext = os.path.splitext(dest)

    for sentence in sentences_from_source(source):
        mmsi = sentence['mmsi']
        if not mmsi:
            mmsi = 'other'
        if mmsi not in writers:
            writers[mmsi] = open("{}-{}{}".format(fname, mmsi, ext), "wt")
        print_sentence_source(sentence.text, writers[mmsi])

    for writer in writers.values():
        writer.close()


class Fields(dict):
    def __init__(self):
        self.values = {}

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        value = value.strip()
        if key and value and len(value) > 0:
            self.values[key] = value

    def __iter__(self):
        return self.values.__iter__()


class SenderInfo:
    def __init__(self):
        self.mmsi = None
        self.sentence_count = 0
        self.type_counts = defaultdict(int)
        self.fields = Fields()

    def add(self, sentence):
        if not self.mmsi:
            self.mmsi = sentence['mmsi']
        self.sentence_count += 1
        self.type_counts[sentence.type_id()] += 1
        if sentence.type_id() == 5:
            self.fields['shipname'] = sentence['shipname']
            self.fields['destination'] = sentence['destination']

    def report(self):
        print("{}:".format(self.mmsi))
        print("   sentences: {}".format(self.sentence_count))
        type_text = ["{}: {}".format(t, self.type_counts[t]) for t in (sorted(self.type_counts))]
        print("       types: {}".format(", ".join(type_text)))
        for field in sorted(self.fields):
            print("  {:11s}: {}".format(field, self.fields[field]))

class MaxMin:
    def __init__(self, starting=None):
        self.min = self.max = starting

    def add(self, value):
        if self.min is None or self.min is None:
            self.min = self.max = value
            return
        if value > self.max:
            self.max = value
        if value < self.min:
            self.min = value


class GeoInfo:
    def __init__(self):
        self.lat = MaxMin()
        self.lon = MaxMin()

    def add(self, latitude, longitude):
        self.lat.add(latitude)
        self.lon.add(longitude)

    def report(self, indent=""):
        print("{}    top left: {}, {}".format(indent, self.lat.max, self.lon.min))
        print("{}bottom right: {}, {}".format(indent, self.lat.min, self.lon.max))


class SentencesInfo:
    def __init__(self):
        self.sentence_count = 0
        self.type_counts = defaultdict(int)
        self.sender_counts = defaultdict(int)
        self.geo_info = GeoInfo()

    def add(self, sentence):
        self.sentence_count += 1
        self.type_counts[sentence.type_id()] += 1
        self.sender_counts[sentence['mmsi']] += 1
        if sentence.type_id() in [1, 2, 3]:
            self.geo_info.add(sentence['lat'], sentence['lon'])


    def report(self):
        print("Found {} senders in {} sentences.".format(len(self.sender_counts), self.sentence_count))
        self.geo_info.report("  ")
        print("   type counts:")
        for i in sorted(self.type_counts):
            print("                {:2d} {:8d}".format(i, self.type_counts[i]))
        print()


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--individual', '-i', is_flag=True)
def info(sources, individual):
    sentences_info = SentencesInfo()
    sender_info = defaultdict(SenderInfo)

    for sentence in sentences_from_sources(sources):
        sentences_info.add(sentence)
        if individual:
            sender_info[sentence['mmsi']].add(sentence)

    sentences_info.report()

    if individual:
        for mmsi in sorted(sender_info):
            sender_info[mmsi].report()
