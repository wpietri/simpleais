from unittest import TestCase
import sys

from simpleais.tools import DensityMap, Bucketer


class TestDensityMap(TestCase):
    def test_empty(self):
        m = DensityMap(3, 3)
        self.assertListEqual([
            '+---+',
            '|   |',
            '|   |',
            '|   |',
            '+---+',
        ], m.to_text())

    def test_corners(self):
        m = DensityMap(3, 3)
        m.add(0, 0)
        m.add(1, 1)
        self.assertListEqual([
            '+---+',
            '|  9|',
            '|   |',
            '|9  |',
            '+---+',
        ], m.to_text())

    def test_other_corners(self):
        m = DensityMap(3, 3)
        m.add(0, 0)
        m.add(-1, 1)
        self.assertListEqual([
            '+---+',
            '|9  |',
            '|   |',
            '|  9|',
            '+---+',
        ], m.to_text())

    def test_point(self):
        m = DensityMap(3, 3)
        m.add(0, 0)
        self.assertListEqual([
            '+---+',
            '|   |',
            '| 9 |',
            '|   |',
            '+---+',
        ], m.to_text())

    def test_line(self):
        """ Slightly weird, might be better in the middle"""
        m = DensityMap(3, 3)
        m.add(0, 0)
        m.add(0, 1)
        m.add(0, 2)
        self.assertListEqual([
            '+---+',
            '|   |',
            '|999|',
            '|   |',
            '+---+',
        ], m.to_text())

    def test_plus(self):
        m = DensityMap(3, 3)
        m.add(1, 0)
        m.add(0, -1)
        m.add(0, 0)
        m.add(0, 1)
        m.add(-1, 0)
        self.assertListEqual([
            '+---+',
            '| 9 |',
            '|999|',
            '| 9 |',
            '+---+',
        ], m.to_text())

    def test_x(self):
        m = DensityMap(3, 3)
        m.add(1, -1)
        m.add(1, 1)
        m.add(0, 0)
        m.add(-1, -1)
        m.add(-1, 1)
        self.assertListEqual([
            '+---+',
            '|9 9|',
            '| 9 |',
            '|9 9|',
            '+---+',
        ], m.to_text())

    def test_l(self):
        m = DensityMap(3, 3)
        m.add(1, -1)
        m.add(0, -1)
        m.add(-1, -1)
        m.add(-1, 0)
        m.add(-1, 1)
        self.assertListEqual([
            '+---+',
            '|9  |',
            '|9  |',
            '|999|',
            '+---+',
        ], m.to_text())

    def test_weight(self):
        m = DensityMap(3, 3)
        m.add(1, 0)
        m.add(0, -1)
        m.add(0, 0)
        m.add(0, 0)
        m.add(0, 0)
        m.add(0, 0)
        m.add(0, 1)
        m.add(-1, 0)
        m.add(-1, 0)
        self.assertListEqual([
            '+---+',
            '| 2 |',
            '|292|',
            '| 4 |',
            '+---+',
        ], m.to_text())

    def test_funky_example(self):
        m = DensityMap(4, 4)
        m.add(33.7419, -118.4680)
        m.add(33.7418, -118.4677)
        m.add(33.7417, -118.4675)
        m.add(33.7415, -118.4672)
        self.assertListEqual([
            '+----+',
            '|99  |',
            '|  9 |',
            '|    |',
            '|   9|',
            '+----+',
        ], m.to_text())


class TestBucketer(TestCase):
    def test_basics(self):
        b = Bucketer(0, 1, 10)
        self.assertEqual(0, b.bucket(0))
        self.assertEqual(0, b.bucket(0.1))
        self.assertEqual(1, b.bucket(0.1001))
        self.assertEqual(9, b.bucket(0.9001))
        self.assertEqual(9, b.bucket(0.9999))
        self.assertEqual(9, b.bucket(1))

    def test_min_equals_max(self):
        b = Bucketer(0, 0, 3)
        self.assertEqual(1, b.bucket(0))  # middle bucket
        b = Bucketer(0, 0, 4)
        self.assertIn(b.bucket(0), [1, 2])  # middle-ish bucket

    def test_real_values(self):
        b = Bucketer(-118.4680, -118.4672, 4)
        self.assertEqual(0, b.bucket(-118.4680))
        self.assertEqual(3, b.bucket(-118.4672))

        b = Bucketer(33.7415, 33.7419, 4)
        self.assertEqual(0, b.bucket(33.7415))
        self.assertEqual(3, b.bucket(33.7419))



def test_bins(self):
    """
     Left as an explanation of how numpy binning works.Basically, you need
     one more bin than you want in buckets, and you have to add epsilon to your
     max value if you want the max value to actually fall in that bucket. I
     think this is so that out-of-range values have a place to go (low go in
     zeroth bucket; high go above).
    """
    min_val = 0
    max_val = 1
    buckets = 10
    values_per_bucket = 10

    import numpy

    data = list(numpy.linspace(min_val, max_val, buckets * values_per_bucket))
    bins = numpy.linspace(min_val, max_val + sys.float_info.epsilon, buckets + 1)
    digitized = numpy.digitize(data, bins)
    counts = numpy.bincount(digitized)
    self.assertEqual(buckets + 1, len(counts))
    self.assertEqual(0, counts[0])
    for bucket in counts[1:]:
        self.assertEqual(values_per_bucket, bucket)
