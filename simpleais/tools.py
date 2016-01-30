import sys

import click

from . import sentences_from_source

# todo: aisburst

def print_sentence_source(text):
    if isinstance(text, str):
        print(text)
    else:
        for line in text:
            print(line)


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
def grep(sources, mmsi):
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
