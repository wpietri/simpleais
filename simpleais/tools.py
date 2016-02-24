import functools
import math
import os
import re
import sys
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from math import radians, sin, atan2, sqrt, cos

import click
import numpy

from simpleais import sentences_from_source

_RADIUS_OF_EARTH = 6373.0

TIME_FORMAT = "%Y/%m/%d %H:%M:%S"


@contextmanager
def wild_disregard_for(e):
    try:
        yield
    except e:
        exit(0)


def print_sentence_source(text, file=None):
    if isinstance(text, str):
        text = [text]
    for line in text:
        if file:
            print(line, file=file)
        else:
            # noinspection PyArgumentList
            print(line, flush=True)


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
def cat(sources):
    for sentence in sentences_from_sources(sources):
        with wild_disregard_for(BrokenPipeError):
            print_sentence_source(sentence.text)


def likes(field, lat, lon, mmsi, sentence, sentence_type):
    factors = [True]
    if len(mmsi) > 0:
        factors.append(sentence['mmsi'] in mmsi)
    if sentence_type:
        factors.append(sentence.type_id() in sentence_type)
    if lon:
        factors.append(sentence.location() is not None and lon[0] < sentence['lon'] < lon[1])
    if lat and sentence.location():
        factors.append(sentence.location() is not None and lat[0] < sentence['lat'] < lat[1])
    if field:
        for f in field:
            factors.append(sentence[f] is not None)
    result = functools.reduce(lambda x, y: x and y, factors)
    return result


class Taster(object):
    pass

    def __init__(self, mmsi=None, sentence_type=None, lon=None, lat=None, field=None, checksum=None):
        self.mmsi = mmsi
        self.sentence_type = sentence_type
        self.lon = lon
        self.lat = lat
        self.field = field
        self.checksum = checksum

    def likes(self, sentence):
        factors = [True]
        if self.mmsi:
            factors.append(sentence['mmsi'] in self.mmsi)
        if self.sentence_type:
            factors.append(sentence.type_id() in self.sentence_type)
        if self.lon:
            factors.append(sentence.location() is not None and self.lon[0] < sentence['lon'] < self.lon[1])
        if self.lat:
            factors.append(sentence.location() is not None and self.lat[0] < sentence['lat'] < self.lat[1])
        if self.field:
            for f in self.field:
                factors.append(sentence[f] is not None)
        if self.checksum is not None:
            factors.append(sentence.check() == self.checksum)
        return functools.reduce(lambda x, y: x and y, factors)


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--mmsi', '-m', multiple=True)
@click.option('--mmsi-file')
@click.option('--type', '-t', 'sentence_type', type=int, multiple=True)
@click.option('--longitude', '--long', '--lon', nargs=2, type=float)
@click.option('--latitude', '--lat', nargs=2, type=float)
@click.option('--field', '-f', multiple=True)
@click.option('--checksum', type=click.Choice(['valid', 'invalid']))
def grep(sources, mmsi=None, mmsi_file=None, sentence_type=None, lon=None, lat=None, field=None, checksum=None):
    if not mmsi:
        mmsi = []
    if mmsi_file:
        mmsi = list(mmsi)
        with open(mmsi_file, "r") as f:
            mmsi.extend([l.strip() for l in f.readlines()])
        mmsi = frozenset(mmsi)
    if checksum is None:
        checksum_desire = None
    else:
        checksum_desire = checksum == "valid"
    taster = Taster(mmsi, sentence_type, lon, lat, field, checksum_desire)
    for sentence in sentences_from_sources(sources):
        with wild_disregard_for(BrokenPipeError):
            if taster.likes(sentence):
                print_sentence_source(sentence.text)


@click.command()
@click.argument('sources', nargs=-1)
def as_text(sources):
    for sentence in sentences_from_sources(sources):
        with wild_disregard_for(BrokenPipeError):
            result = []
            if sentence.time:
                result.append(sentence.time.strftime(TIME_FORMAT))
            result.append("{:2}".format(sentence.type_id()))
            result.append("{:9}".format(str(sentence['mmsi'])))
            if sentence['dest_mmsi']:
                result.append("-> {:9}".format(str(sentence['dest_mmsi'])))
            if sentence.type_id() == 21:
                result.append("{}".format(sentence['name']))
            location = sentence.location()
            if location:
                result.append("{:9.4f} {:9.4f}".format(location[0], location[1]))
            if sentence.type_id() == 5:
                result.append("{}->{}".format(sentence['shipname'], sentence['destination']))
            elif sentence.type_id() in [12, 14]:
                result.append("{}".format(sentence['text']))
            elif sentence.type_id() == 24 and sentence['partno'] == 0:
                result.append("{}".format(sentence['shipname']))

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

    def report(self, file=sys.stdout):
        print("{}:".format(self.mmsi), file=file)
        print("    sentences: {}".format(self.sentence_count), file=file)
        type_text = ["{}: {}".format(t, self.type_counts[t]) for t in (sorted(self.type_counts))]
        print("        types: {}".format(", ".join(type_text)), file=file)
        for field in sorted(self.fields):
            print("  {:>11s}: {}".format(field, self.fields[field]), file=file)


class MaxMin:
    def __init__(self, starting=None):
        self.min = self.max = starting

    def valid(self):
        return self.min is not None and self.min is not None

    def add(self, value):
        if not self.valid():
            self.min = self.max = value
            return
        if value > self.max:
            self.max = value
        if value < self.min:
            self.min = value

    def range(self):
        if self.valid:
            return self.max - self.min

    def mid(self):
        if self.valid:
            return (self.max + self.min) / 2


class GeoInfo:
    """
    This behaves weirdly with smaller areas that cross the dateline; it will show a whole world map.
    """
    def __init__(self):
        self.lon = MaxMin()
        self.lat = MaxMin()

    def add(self, point):
        self.lon.add(point[0])
        self.lat.add(point[1])

    def report(self, indent="", file=sys.stdout):
        if not self.valid():
            return
        print("{}    top left: {:.4f}, {:.4f}".format(indent, self.lon.min, self.lat.max), file=file)
        print("{}bottom right: {:.4f}, {:.4f}".format(indent, self.lon.max, self.lat.min), file=file)
        print("{}       width: {:.2f} km".format(indent, self.width()), file=file)
        print("{}      height: {:.2f} km".format(indent, self.height()), file=file)

    def width(self):
        result = distance((self.lon.min, self.lat.mid()), (self.lon.max, self.lat.mid()))
        if self.lon.range() <= 180:
            return result
        else:
            return _RADIUS_OF_EARTH * math.pi * 2 - result

    def height(self):
        return distance((self.lon.mid(), self.lat.min), (self.lon.mid(), self.lat.max))

    def __str__(self, *args, **kwargs):
        return "GeoInfo(latmin={}, latmax={}, lonmin={}, lonmax={})".format(self.lat.min, self.lat.max,
                                                                            self.lon.min, self.lon.max)

    def valid(self):
        return self.lon.valid() and self.lat.valid()


def distance(p1, p2):
    lon1 = radians(p1[0])
    lat1 = radians(p1[1])
    lon2 = radians(p2[0])
    lat2 = radians(p2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    d = _RADIUS_OF_EARTH * c
    return d


class SentencesInfo:
    def __init__(self, by_type=False):
        self.by_type = by_type
        self.sentence_count = 0
        self.bad_checksum_count = 0
        self.time_range = MaxMin()
        if by_type:
            self.type_counts = defaultdict(int)
        self.sender_counts = defaultdict(int)

    def add(self, sentence):
        self.sentence_count += 1
        if sentence.time:
            self.time_range.add(sentence.time.timestamp())
        if self.by_type:
            self.type_counts[sentence.type_id()] += 1
        self.sender_counts[sentence['mmsi']] += 1

    def count_bad_checksum(self):
        self.bad_checksum_count += 1

    def report(self, file=sys.stdout):
        if self.sentence_count < 1:
            print("No sentences found.", file=file)
            return
        print("Found {} senders in {} good sentences with {} invalid ({:0.2f}%).".format(
            len(self.sender_counts),
            self.sentence_count,
            self.bad_checksum_count,
            100.0 * self.bad_checksum_count / (self.sentence_count + self.bad_checksum_count)
        ), file=file)
        if self.time_range.valid() and self.time_range.range() > 0:
            m, s = divmod(self.time_range.range(), 60)
            h, m = divmod(m, 60)
            print("Starting on {} and running for {:02.0f}h{:02.0f}m{:02.0f}s.".format(
                datetime.fromtimestamp(self.time_range.min).strftime(TIME_FORMAT),
                h, m, s), file=file)

        if self.sentence_count > 0:
            if self.by_type:
                print("   type counts:", file=file)
                for i in sorted(self.type_counts):
                    print("                {:2d} {:8d}".format(i, self.type_counts[i]), file=file)
                print(file=file)


class Bucketer:
    """Given min, max, and buckets, buckets values"""

    def __init__(self, min_val, max_val, bucket_count):
        self.min_val = min_val
        self.max_val = max_val
        self.bucket_count = bucket_count
        self.max_buckets = bucket_count - 1
        if self.min_val == self.max_val:
            self.bins = numpy.linspace(min_val - 1, max_val + 1, bucket_count + 1)
        else:
            self.bins = numpy.linspace(min_val, max_val + sys.float_info.epsilon, bucket_count + 1)

    def bucket(self, value):
        result = numpy.digitize(value, self.bins) - 1

        # this shouldn't be necessary, but it somehow is
        if result > self.max_buckets:
            return self.max_buckets
        return result

    def __str__(self, *args, **kwargs):
        return "Bucketer({}, {}, {}, {})".format(self.min_val, self.max_val, self.bucket_count, self.bins)


class DensityMap:
    def __init__(self, width=60, height_scale=0.5, indent=""):
        self.desired_width = width
        self.height_scale = height_scale  # terminal characters are about 2x tall as they are wide
        self.indent = indent
        self.geo_info = GeoInfo()
        self.points = []
        self.marks = []
        self.cached_height = None

    def add(self, point):
        self.points.append(point)
        self.geo_info.add(point)
        if self.cached_height is not None:
            self.cached_height = None

    def valid(self):
        return len(self.points) > 0 and self.geo_info.valid()

    def bucket(self, points):
        xb = Bucketer(self.geo_info.lon.min, self.geo_info.lon.max, self.width())
        yb = Bucketer(self.geo_info.lat.min, self.geo_info.lat.max, self.height())
        result = []
        for point in points:
            x = xb.bucket(point[0])
            y = self.height() - 1 - yb.bucket(point[1])
            result.append((x, y))
        return result

    def height(self):
        if self.cached_height is None:
            if self.geo_info.valid() and self.geo_info.width() > 0 and self.geo_info.height() > 0:
                self.cached_height = int(
                    self.height_scale * self.geo_info.height() * self.width() / self.geo_info.width())
            else:
                self.cached_height = int(self.height_scale * self.width())
        return self.cached_height

    def width(self):
        return self.desired_width

    def to_counts(self):
        # noinspection PyUnusedLocal
        results = [[0 for ignored in range(self.width())] for ignored in range(self.height())]
        if self.geo_info.valid():
            for x, y in self.bucket(self.points):
                results[y][x] += 1
            for x, y in self.bucket(self.marks):
                results[y][x] = -1
        return results

    def to_text(self):
        counts = self.to_counts()

        max_count = max([max(l) for l in counts])

        def value_to_text(value):
            if value == -1:
                return "*"
            elif value == 0:
                return " "
            else:
                c = str(int(9.99999 * value / max_count))
                if c == '0':
                    return '.'
                return c

        output = []
        header_footer_line = "{}+{}+".format(self.indent, "-" * self.width())
        output.append(header_footer_line)
        for row in counts:
            line = []
            for col in row:
                line.append(value_to_text(col))
            output.append("{}|{}|".format(self.indent, "".join(line)))
        output.append(header_footer_line)
        return output

    def show(self, file=sys.stdout):
        print("\n".join(self.to_text()), file=file)

    def mark(self, point):
        self.marks.append(point)
        self.geo_info.add(point)



@click.command()
@click.argument('sources', nargs=-1)
@click.option('--individual', '-i', is_flag=True)
@click.option('--map', '-m', "show_map", is_flag=True)
@click.option('--by-type', '-t', is_flag=True)
@click.option('--point', '-p', type=(float, float), multiple=True)
def info(sources, individual, by_type, show_map, point):
    sentences_info = SentencesInfo(by_type)
    sender_info = defaultdict(SenderInfo)
    geo_info = GeoInfo()

    map_info = DensityMap()
    if point:
        for p in point:
            map_info.mark(p)

    for sentence in sentences_from_sources(sources):
        try:
            if not sentence.check():
                sentences_info.count_bad_checksum()
                continue

            sentences_info.add(sentence)

            loc = sentence.location()
            if loc:
                geo_info.add(loc)
                if show_map:
                    map_info.add(loc)

            if individual:
                sender_info[sentence['mmsi']].add(sentence)
        except:
            print("Unexpected failure for sentence", sentence.text, file=sys.stderr)
            raise

    with wild_disregard_for(BrokenPipeError):
        sentences_info.report(file=sys.stdout)

        if geo_info.valid():
            geo_info.report("  ", file=sys.stdout)

        if show_map and map_info.valid():
            map_info.show(file=sys.stdout)

        if individual:
            for mmsi in sorted(sender_info):
                sender_info[mmsi].report(file=sys.stdout)


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--bits', '-b', is_flag=True)
def dump(sources, bits):
    sentence_count = 0
    for sentence in sentences_from_sources(sources):
        with wild_disregard_for(BrokenPipeError):
            if sentence_count != 0:
                print()
            sentence_count += 1
            print("Sentence {}:".format(sentence_count))
            if sentence.time:
                print("          time: {}".format(sentence.time.strftime(TIME_FORMAT)))
            for t in sentence.text:
                print("          text: {}".format(re.search("!.*", t).group(0)))
            print("        length: {}".format(len(sentence.message_bits())))
            if bits:
                bit_lumps = list(chunks(str(sentence.message_bits()), 6))
                groups = chunks(bit_lumps, 8)
                pos = 0
                print("         check: {}".format(", ".join([str(c) for c in sentence.checksum_valid])))
                print("          bits: {:3d} {}".format(pos, " ".join(groups.__next__())))
                for group in groups:
                    pos += 48
                    print("          bits: {:3d} {}".format(pos, " ".join(group)))

            for field in sentence.fields():
                value = '-'
                if field.valid():
                    value = field.value()
                if bits:
                    print("  {:>12}: {} ({})".format(field.name(), value, field.bits()))
                else:
                    print("  {:>12}: {}".format(field.name(), value))

# used for profiling; call with something like "grep ../tests/sample.ais -t 20"
if __name__ == "__main__":
    print("running", sys.argv[1], "with", sys.argv[2:], file=sys.stderr)
    globals()[sys.argv[1]](sys.argv[2:])
