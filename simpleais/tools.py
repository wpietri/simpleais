import click

from . import sentences_from_source


def print_sentence(text):
    if isinstance(text, str):
        print(text)
    else:
        for line in text:
            print(line)


@click.command()
@click.argument('sources', nargs=-1)
def grep(sources):
    for source in sources:
        for sentence in sentences_from_source(source):
            print_sentence(sentence.text)
