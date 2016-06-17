import functools
import math
import os
import re
import sys
from collections import defaultdict
from contextlib import contextmanager
from copy import copy
from math import radians, sin, atan2, sqrt, cos
from time import localtime
from time import strftime

import click
import numpy
from dateutil.parser import parse as dateutil_parse

from simpleais import sentences_from_source

_RADIUS_OF_EARTH = 6373.0


@contextmanager
def wild_disregard_for(e):
    try:
        yield
    except e:
        exit(0)


def time_to_text(t):
    return strftime("%Y/%m/%d %H:%M:%S", localtime(t))


def print_sentence_source(sentence, file=None):
    text = sentence.text
    if isinstance(text, str):
        text = [text]
    for line in text:
        if sentence.time:
            output = "{:.3f} {}".format(sentence.time, line)
        else:
            output = line

        if file:
            print(output, file=file)
        else:
            # noinspection PyArgumentList
            print(output, flush=True)


def sentences_from_sources(sources, log_errors=False):
    if len(sources) > 0:
        for source in sources:
            for sentence in sentences_from_source(source, log_errors):
                yield sentence
    else:
        for sentence in sentences_from_source(sys.stdin, log_errors):
            yield sentence


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--verbose', is_flag=True)
def cat(sources, verbose):
    """ Prints out all complete AIS transmissions.  """
    for sentence in sentences_from_sources(sources, log_errors=verbose):
        with wild_disregard_for(BrokenPipeError):
            print_sentence_source(sentence)


class Taster(object):
    pass

    def __init__(self, mmsi=None, sentence_type=None, vessel_class=None, lon=None, lat=None, field=None, value=None,
                 before=None, after=None, mode='and', checksum=None, invert_match=False):
        self.mmsi = mmsi
        self.sentence_type = sentence_type
        self.vessel_class = vessel_class
        self.lon = lon
        self.lat = lat
        self.field = field
        self.value = value
        self.before = before
        self.after = after
        if mode == 'and' or mode is None:
            self.default_result = [True]
            self.reducer = lambda x, y: x and y
        elif mode == 'or':
            self.default_result = [False]
            self.reducer = lambda x, y: x or y
        else:
            raise ValueError("unknown mode {}".format(mode))
        self.checksum = checksum
        self.invert_match = invert_match

    def likes(self, sentence):
        factors = copy(self.default_result)
        if self.mmsi:
            factors.append(sentence['mmsi'] in self.mmsi)
        if self.sentence_type:
            factors.append(sentence.type_id() in self.sentence_type)
        if self.vessel_class:
            if self.vessel_class == 'a':
                factors.append(sentence.type_id() in [1, 2, 3, 5])
            elif self.vessel_class == 'b':
                factors.append(sentence.type_id() in [18, 19, 24])
        if self.lon or self.lat:
            loc = sentence.location()
            if self.lon:
                factors.append(loc is not None and self.lon[0] <= loc[0] <= self.lon[1])
            if self.lat:
                factors.append(loc is not None and self.lat[0] <= loc[1] <= self.lat[1])
        if self.field:
            for f in self.field:
                factors.append(sentence[f] is not None)
        if self.value:
            for f, v in self.value:
                factors.append(sentence[f] == v or str(sentence[f]) == str(v))
        if self.before:
            factors.append(sentence.time <= self.before)
        if self.after:
            factors.append(self.after <= sentence.time)
        if self.checksum is not None:
            factors.append(sentence.check() == self.checksum)
        result = functools.reduce(self.reducer, factors)
        if self.invert_match:
            return not result
        else:
            return result


def parse_date(string):
    if string:
        return int(dateutil_parse(string).strftime("%s"))
    else:
        return None


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--mmsi', '-m', multiple=True)
@click.option('--mmsi-file')
@click.option('--type', '-t', 'sentence_type', type=int, multiple=True)
@click.option('--class', 'vessel_class', type=click.Choice(['a', 'b']))
@click.option('--longitude', '--long', '--lon', nargs=2, type=float)
@click.option('--latitude', '--lat', nargs=2, type=float)
@click.option('--field', '-f', multiple=True)
@click.option('--value', type=(str, str), multiple=True)
@click.option('--before')
@click.option('--after')
@click.option('--checksum', type=click.Choice(['valid', 'invalid']))
@click.option('--mode', type=click.Choice(['and', 'or']))
@click.option('--invert-match', '-v', is_flag=True)
@click.option('--verbose', is_flag=True)
def grep(sources, mmsi=None, mmsi_file=None, sentence_type=None, vessel_class=None, lon=None, lat=None,
         value=None, before=None, after=None, field=None, checksum=None,
         mode='and', invert_match=False, verbose=False):
    """ Filters AIS transmissions.  """
    if not mmsi:
        mmsi = frozenset()
    if mmsi_file:
        mmsi = frozenset(mmsi)
        mmsi = mmsi.union(read_mmsi_file(mmsi_file))
    if checksum is None:
        checksum_desire = None
    else:
        checksum_desire = checksum == "valid"
    taster = Taster(mmsi, sentence_type, vessel_class, lon, lat, field, value, parse_date(before), parse_date(after),
                    mode, checksum_desire, invert_match)
    with wild_disregard_for(BrokenPipeError):
        for sentence in sentences_from_sources(sources, log_errors=verbose):
            if taster.likes(sentence):
                print_sentence_source(sentence)


def read_mmsi_file(mmsi_file):
    with open(mmsi_file, "r") as f:
        return frozenset([l.strip() for l in f.readlines()])


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--verbose', is_flag=True)
def as_text(sources, verbose):
    """ Simple text display, one line per AIS sentence. """
    for sentence in sentences_from_sources(sources, log_errors=verbose):
        with wild_disregard_for(BrokenPipeError):
            result = []
            if sentence.time:
                t = sentence.time
                result.append(time_to_text(t))
            result.append("{:2}".format(sentence.type_id()))
            result.append("{:9}".format(str(sentence['mmsi'])))
            if sentence['dest_mmsi']:
                result.append("-> {:9}".format(str(sentence['dest_mmsi'])))
            if sentence.type_id() == 21:
                result.append("{}".format(sentence['name']))
            location = sentence.location()
            if location:
                result.append("{:9.4f} {:9.4f}".format(location[0], location[1]))
                if sentence['speed'] and sentence['speed'] < 102.3:
                    result.append("{}kn".format(sentence['speed']))
                if sentence['course'] and sentence['course'] < 360:
                    if sentence['heading'] and sentence['heading'] < 360:
                        result.append("{}°/{}°".format(sentence['course'], sentence['heading']))
                    else:
                        result.append("{}°".format(sentence['course']))

            # ship info
            if sentence['shipname']:
                result.append(sentence['shipname'])
            if sentence['to_bow'] and sentence['to_bow'] > 0:
                result.append("({})".format(dimensions_as_text(sentence)))
            if sentence['destination']:
                result.append("-> {}".format(sentence['destination']))
                if sentence['minute'] and sentence['minute'] < 60:
                    result.append("at {}/{} {}:{:02d}".format(
                        sentence['month'], sentence['day'],
                        sentence['hour'], sentence['minute']))
            elif sentence.type_id() in [12, 14]:
                result.append("{}".format(sentence['text']))
            elif sentence.type_id() == 24 and sentence['partno'] == 0:
                result.append("{}".format(sentence['shipname']))

            if sentence['time']:
                result.append(time_to_text(sentence['time']))

            print(" ".join(result))


def dimensions_as_text(type_5_sentence):
    if type_5_sentence['to_bow'] and type_5_sentence['to_bow'] > 0:
        return "{}x{}x{}m".format(
            type_5_sentence['to_bow'] + type_5_sentence['to_stern'],
            type_5_sentence['to_port'] + type_5_sentence['to_starboard'],
            type_5_sentence['draught'])


@click.command()
@click.argument('source', nargs=1)
@click.argument('dest', nargs=1, required=False)
@click.option('--verbose', is_flag=True)
def burst(source, dest, verbose):
    """ Takes large AIS files and splits them up by sender. """
    if not dest:
        dest = source
    writers = {}
    fname, ext = os.path.splitext(dest)

    for sentence in sentences_from_source(source, log_errors=verbose):
        mmsi = sentence['mmsi']
        if not mmsi:
            mmsi = 'other'
        if mmsi not in writers:
            writers[mmsi] = open("{}-{}{}".format(fname, mmsi, ext), "wt")
        print_sentence_source(sentence, writers[mmsi])

    for writer in writers.values():
        writer.close()


class FieldsHistory:
    def __init__(self):
        self.values = defaultdict(list)

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        value = value.strip()
        if key and value and len(value) > 0:
            if value not in (self.values[key]):
                self.values[key].append(value)

    def __iter__(self):
        return self.values.__iter__()


class SenderInfo:
    def __init__(self):
        self.mmsi = None
        self.sentence_count = 0
        self.type_counts = defaultdict(int)
        self.fields = FieldsHistory()

    def add(self, sentence):
        if not self.mmsi:
            self.mmsi = sentence['mmsi']
        self.sentence_count += 1
        self.type_counts[sentence.type_id()] += 1
        if sentence.type_id() == 5:
            self.fields['shipname'] = sentence['shipname']
            self.fields['destination'] = sentence['destination']
            self.fields['dimensions'] = dimensions_as_text(sentence)

    def report(self, file=sys.stdout):
        print("{}:".format(self.mmsi), file=file)
        print("    sentences: {}".format(self.sentence_count), file=file)
        type_text = ["{}: {}".format(t, self.type_counts[t]) for t in (sorted(self.type_counts))]
        print("        types: {}".format(", ".join(type_text)), file=file)
        for field in sorted(self.fields):
            print("  {:>11s}: {}".format(field, ", ".join(self.fields[field])), file=file)


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
            self.time_range.add(sentence.time)
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
                time_to_text(self.time_range.min),
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
        return min(self.desired_width, max(1, self.cached_height))

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
@click.option('--verbose', is_flag=True)
def info(sources, individual, by_type, show_map, point, verbose):
    """ Summarizes AIS transmissions. """
    sentences_info = SentencesInfo(by_type)
    sender_info = defaultdict(SenderInfo)
    geo_info = GeoInfo()

    map_info = DensityMap()
    if point:
        for p in point:
            map_info.mark(p)

    for sentence in sentences_from_sources(sources, log_errors=verbose):
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
    # Yield successive n-sized chunks from l.
    for i in range(0, len(l), n):
        yield l[i:i + n]


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--bits', '-b', is_flag=True)
@click.option('--verbose', is_flag=True)
def dump(sources, bits, verbose):
    """ Gives a detailed dump of each AIS sentence. """
    sentence_count = 0
    for sentence in sentences_from_sources(sources, log_errors=verbose):
        with wild_disregard_for(BrokenPipeError):
            if sentence_count != 0:
                print()
            sentence_count += 1
            print("Sentence {}:".format(sentence_count))
            if sentence.time:
                print("          time: {}".format(time_to_text(sentence.time)))
            for t in sentence.text:
                print("          text: {}".format(re.search("!.*", t).group(0)))
            print("        length: {}".format(len(sentence.message_bits())))
            if bits:
                bit_lumps = list(chunks(str(sentence.message_bits()), 6))
                groups = chunks(bit_lumps, 8)
                pos = 0
                print("         check: {}".format(", ".join([str(c) for c in sentence.fragment_checksum_validity()])))
                print("          bits: {:3d} {}".format(pos, " ".join(groups.__next__())))
                for group in groups:
                    pos += 48
                    print("          bits: {:3d} {}".format(pos, " ".join(group)))

            for field in sentence.fields():
                value = '-'
                if field.valid():
                    value = field.value()
                    if field.value() == 1456559999:
                        print(field)
                    if field.name() == 'time':
                        print("foo")
                        value = time_to_text(value)
                if bits:
                    print("  {:>12}: {} ({})".format(field.name(), value, field.bits()))
                else:
                    print("  {:>12}: {}".format(field.name(), value))


def value_for(field, sentence):
    if sentence.time and field in ('time-date', 'time-hour', 'time-minute'):
        if field == 'time-date':
            return strftime("%Y/%m/%d", localtime(sentence.time))
        elif field == 'time-hour':
            return strftime("%H", localtime(sentence.time))
        elif field == 'time-minute':
            return strftime("%M", localtime(sentence.time))
    elif field == 'geo-degree':
        lon = sentence['lon']
        lat = sentence['lat']
        if lon and lat:
            return "{:+3.0f}x{:+2.0f}".format(lon, lat)
    else:
        return sentence[field]


def value_tuple_for(fields, sentence):
    result = tuple([value_for(field, sentence) for field in fields])
    if all(item is None for item in result):
        return None
    else:
        return result


def tuple_display(t):
    if len(t) == 1:
        return str(t[0])
    else:
        return "+".join([str(i) for i in t])


@click.command()
@click.argument('sources', nargs=-1)
@click.option('--field', '-f', 'fields', multiple=True)
@click.option('--date', 'fields', flag_value='time-date', multiple=True)
@click.option('--hour', 'fields', flag_value='time-hour', multiple=True)
@click.option('--minute', 'fields', flag_value='time-minute', multiple=True)
@click.option('--degree', 'fields', flag_value='geo-degree', multiple=True)
@click.option('--count', '-c', 'output', flag_value='count', default=True)
@click.option('--hist', '-h', 'output', flag_value='hist')
@click.option('--verbose', is_flag=True)
def stat(sources, fields, output, verbose):
    if not fields or len(fields) < 1:
        raise click.UsageError("at least one field required; try --hour or -f type")
    counts = defaultdict(int)
    for sentence in sentences_from_sources(sources, log_errors=verbose):
        val = value_tuple_for(fields, sentence)
        if val:
            counts[val] += 1

    key_width = max([len(str(tuple_display(k))) for k in counts.keys()], default=0)
    val_width = max([len(str(v)) for v in counts.values()], default=0)
    if output == 'count':
        for key in sorted(counts, key=lambda k: counts[k], reverse=True):
            print("{key:{key_width}}  {value:{val_width}}".format(
                key=tuple_display(key), value=counts[key],
                key_width=key_width, val_width=val_width)
            )
    else:
        largest = max(counts.values())
        for key in sorted(counts):
            print("{key:{key_width}}  {value:{val_width}}  {hist}".format(
                key=tuple_display(key), value=counts[key],
                key_width=key_width, val_width=val_width,
                hist="*" * int(1 + 40 * counts[key] // largest))
            )


# used for profiling; call with something like "grep ../tests/sample.ais -t 20"
if __name__ == "__main__":
    print("running", sys.argv[1], "with", sys.argv[2:], file=sys.stderr)
    globals()[sys.argv[1]](sys.argv[2:])
