import click

from . import sentences_from_source

# todo: stdin handling
# todo: aisburst

def print_sentence(text):
    if isinstance(text, str):
        print(text)
    else:
        for line in text:
            print(line)


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--mmsi', '-m', multiple=True)
def grep(sources, mmsi):
    for source in sources:
        for sentence in sentences_from_source(source):
            if len(mmsi) > 0:
                if sentence['mmsi'] in mmsi:
                    print_sentence(sentence.text)
            else:
                print_sentence(sentence.text)


@click.command()
@click.argument('sources', nargs=-1)
def as_text(sources):
    for source in sources:
        for sentence in sentences_from_source(source):
            print("{} {:2} {:10}".format(sentence.time, sentence.type_id(), str(sentence['mmsi'])))




