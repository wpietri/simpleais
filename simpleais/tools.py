import os
import sys

import click

from . import sentences_from_source

# todo: aisburst

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
def grep(sources, mmsi, mmsi_file = None):
    if (mmsi_file):
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
        if not mmsi in writers:
            writers[mmsi] = open( "{}-{}{}".format(fname, mmsi, ext), "wt")
        print_sentence_source(sentence.text, writers[mmsi])

    for writer in writers.values():
        writer.close()
