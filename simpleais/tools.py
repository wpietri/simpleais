from collections import defaultdict
import functools
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
@click.option('--type', '-t', type=int)
@click.option('--latitude', '--lat', nargs=2, type=float)
@click.option('--longitude', '--lon', nargs=2, type=float)
def grep(sources, mmsi, mmsi_file=None, type=None, lat=None, lon=None):
    if mmsi_file:
        mmsi = list(mmsi)
        with open(mmsi_file, "r") as f:
            mmsi.extend([l.strip() for l in f.readlines()])
        mmsi = frozenset(mmsi)
    for sentence in sentences_from_sources(sources):
        factors = [True]

        if len(mmsi) > 0:
            factors.append(sentence['mmsi'] in mmsi)
        if type:
            factors.append(sentence.type_id() == type)
        if lat:
            factors.append(sentence['lat'] and lat[0] < sentence['lat'] < lat[1])
        if lon:
            factors.append(sentence['lon'] and lon[0] < sentence['lon'] < lon[1])

        if functools.reduce(lambda x, y: x and y, factors):
            print_sentence_source(sentence.text)


@click.command()
@click.argument('sources', nargs=-1)
def as_text(sources):
    for sentence in sentences_from_sources(sources):
        result = []
        result.append(sentence.time.strftime("%Y/%m/%d %H:%M:%S"))
        result.append("{:2}".format(sentence.type_id()))
        result.append("{:9}".format(str(sentence['mmsi'])))
        if sentence['lat']:
            result.append("{:9.4f} {:9.4f}".format(sentence['lat'], sentence['lon']))
        elif sentence.type_id() == 5:
            result.append("{}->{}".format(sentence['shipname'], sentence['destination']))

        print(" ".join(result))


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


class Fields:
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
        print("    sentences: {}".format(self.sentence_count))
        type_text = ["{}: {}".format(t, self.type_counts[t]) for t in (sorted(self.type_counts))]
        print("        types: {}".format(", ".join(type_text)))
        for field in sorted(self.fields):
            print("  {:>11s}: {}".format(field, self.fields[field]))


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
        if sentence['lat']:
            self.geo_info.add(sentence['lat'], sentence['lon'])

    def report(self):
        print("Found {} senders in {} sentences.".format(len(self.sender_counts), self.sentence_count))
        print("   type counts:")
        for i in sorted(self.type_counts):
            print("                {:2d} {:8d}".format(i, self.type_counts[i]))
        print()
        self.geo_info.report("  ")


class DensityMap:
    def __init__(self, width=60, height=20):
        self.width = width
        self.height = height
        self.geo_info = GeoInfo()
        self.points = []

    def add(self, latitude, longitude):
        self.points.append((latitude, longitude))
        self.geo_info.add(latitude, longitude)

    def show(self):
        # noinspection PyUnusedLocal
        results = [[0 for ignored in range(self.width)] for ignored in range(self.height)]
        x_scale = (self.geo_info.lon.max - self.geo_info.lon.min) / self.width
        y_scale = (self.geo_info.lat.max - self.geo_info.lat.min) / self.height
        for lat, lon in self.points:
            x = int((lon - self.geo_info.lon.min - 0.001) / x_scale)
            y = self.height - 1 - int((lat - self.geo_info.lat.min - 0.001) / y_scale)
            results[y][x] += 1
        max_count = max([max(l) for l in results])

        def c(col):
            if col == 0:
                return " "
            return str(int(9.999 * col / max_count))

        print("  +{}+".format("-" * self.width))
        for row in results:
            print("  |{}|".format("".join([c(col) for col in row])))
        print("  +{}+".format("-" * self.width))


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--individual', '-i', is_flag=True)
@click.option('--map', '-m', "show_map", is_flag=True)
def info(sources, individual, show_map):
    sentences_info = SentencesInfo()
    sender_info = defaultdict(SenderInfo)
    map_info = DensityMap()

    for sentence in sentences_from_sources(sources):
        sentences_info.add(sentence)
        if show_map:
            if sentence['lat']:
                map_info.add(sentence['lat'], sentence['lon'])
        if individual:
            sender_info[sentence['mmsi']].add(sentence)

    sentences_info.report()
    if show_map:
        map_info.show()

    if individual:
        for mmsi in sorted(sender_info):
            sender_info[mmsi].report()
