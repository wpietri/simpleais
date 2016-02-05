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


class SenderInfo:
    def __init__(self, mmsi):
        self.mmsi = mmsi
        self.sentence_count = 0

    def add(self, sentence):
        self.sentence_count += 1

    def report(self):
        print(self.mmsi, self.sentence_count)


class SentencesInfo:
    def __init__(self):
        self.sentence_count = 0
        self.type_counts = defaultdict(int)
        self.sender_counts = defaultdict(int)

    def add(self, sentence):
        self.sentence_count += 1
        self.type_counts[sentence.type_id()] += 1
        self.sender_counts[sentence['mmsi']] += 1

    def report(self):
        print("Found {} senders in {} sentences.".format(len(self.sender_counts), self.sentence_count))
        print()
        print("type counts:")
        for i in sorted(self.type_counts):
            print("  {:2d}\t{:8d}".format(i, self.type_counts[i]))


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--individual', '-i')
def info(sources, individual=False):
    info = SentencesInfo()
    if individual:
        sender_info = defaultdict(SenderInfo)

    for sentence in sentences_from_sources(sources):
        info.add(sentence)
        if individual:
            sender_info[sentence['mmsi']].add(sentence)

    info.report()
    if individual:
        for mmsi in sorted(sender_info):
            sender_info[mmsi].report()
