from unittest import TestCase

from simpleais import parse
from simpleais.tools import *


class TestGeoInfo(TestCase):
    def test_small_area(self):
        g = GeoInfo()
        g.add((-122.4775, 37.8108))  # Fort Point
        g.add((-122.4321, 37.8065))  # Fort Mason
        self.assertEqual(-122.4775, g.lon.min)
        self.assertEqual(-122.4321, g.lon.max)
        self.assertEqual(37.8065, g.lat.min)
        self.assertEqual(37.8108, g.lat.max)
        self.assertAlmostEqual(3.99, g.width(), 3)
        self.assertAlmostEqual(0.48, g.height(), 2)

    def test_the_whole_world(self):
        # I'm not totally sure this is the right behavior, but let's go with it for now.
        g = GeoInfo()
        g.add((-179, 0))
        g.add((0, 0))
        g.add((179, 0))
        self.assertAlmostEqual(39820, g.width(), 0)
        self.assertAlmostEqual(0, g.height(), 0)

        # TODO: test large but not huge areas
        # TODO: test an area near the poles
        # TODO: test an area that crosses the equator
        # TODO: test an area that crosses the dateline
        # TODO: test an area that is more than half the earth


class TestDensityMap(TestCase):
    def test_empty(self):
        m = DensityMap(3, height_scale=1)
        self.assertListEqual([
            '+---+',
            '|   |',
            '|   |',
            '|   |',
            '+---+',
        ], m.to_text())

    def test_corners(self):
        m = DensityMap(3, height_scale=1)
        m.add((0, 0))
        m.add((1, 1))
        self.assertListEqual([
            '+---+',
            '|  9|',
            '|   |',
            '|9  |',
            '+---+',
        ], m.to_text())

    def test_other_corners(self):
        m = DensityMap(3, height_scale=1)
        m.add((0, 0))
        m.add((1, -1))
        self.assertListEqual([
            '+---+',
            '|9  |',
            '|   |',
            '|  9|',
            '+---+',
        ], m.to_text())

    def test_single_data_point(self):
        m = DensityMap(3, height_scale=1)
        m.add((0, 0))
        self.assertListEqual([
            '+---+',
            '|   |',
            '| 9 |',
            '|   |',
            '+---+',
        ], m.to_text())

    def test_line(self):
        m = DensityMap(3, height_scale=1)
        m.add((0, 0))
        m.add((1, 0))
        m.add((2, 0))
        self.assertListEqual([
            '+---+',
            '|   |',
            '|999|',
            '|   |',
            '+---+',
        ], m.to_text())

    def test_plus(self):
        m = DensityMap(3, height_scale=1)
        m.add((1, 0))
        m.add((0, -1))
        m.add((0, 0))
        m.add((0, 1))
        m.add((-1, 0))
        self.assertListEqual([
            '+---+',
            '| 9 |',
            '|999|',
            '| 9 |',
            '+---+',
        ], m.to_text())

    def test_x(self):
        m = DensityMap(3, height_scale=1)
        m.add((1, -1))
        m.add((1, 1))
        m.add((0, 0))
        m.add((-1, -1))
        m.add((-1, 1))
        self.assertListEqual([
            '+---+',
            '|9 9|',
            '| 9 |',
            '|9 9|',
            '+---+',
        ], m.to_text())

    def test_l(self):
        m = DensityMap(3, height_scale=1)
        m.add((1, -1))
        m.add((0, -1))
        m.add((-1, -1))
        m.add((-1, 0))
        m.add((-1, 1))
        self.assertListEqual([
            '+---+',
            '|9  |',
            '|9  |',
            '|999|',
            '+---+',
        ], m.to_text())

    def test_weight(self):
        m = DensityMap(3, height_scale=1)
        m.add((1, 0))
        m.add((0, -1))
        m.add((0, 0))
        m.add((0, 0))
        m.add((0, 0))
        m.add((0, 0))
        m.add((0, 1))
        m.add((-1, 0))
        m.add((-1, 0))
        self.assertListEqual([
            '+---+',
            '| 2 |',
            '|492|',
            '| 2 |',
            '+---+',
        ], m.to_text())

    def test_very_narrow(self):
        m = DensityMap(4, height_scale=1)
        m.add((49.5124, 33.7578))
        m.add((-118.2598, 33.7579))
        self.assertListEqual([
            '+----+',
            '|9  9|',
            '+----+',
        ], m.to_text())

    def test_very_tall(self):
        m = DensityMap(4, height_scale=1)
        m.add((49.5123, -33.7578))
        m.add((49.5123, 33.7578))
        self.assertListEqual([
            '+----+',
            '|  9 |',
            '|    |',
            '|    |',
            '|  9 |',
            '+----+',
        ], m.to_text())

    def test_mark(self):
        m = DensityMap(3, height_scale=1)
        m.add((-1, -1))
        m.add((1, 1))
        m.mark((0, 0))
        self.assertListEqual([
            '+---+',
            '|  9|',
            '| * |',
            '|9  |',
            '+---+',
        ], m.to_text())

    def test_mark_off_screen(self):
        m = DensityMap(3, height_scale=1)
        m.add((-1, -1))
        m.add((1, 1))
        m.mark((3, 3))
        self.assertListEqual([
            '+---+',
            '|  *|',
            '| 9 |',
            '|9  |',
            '+---+',
        ], m.to_text())

    def test_funky_example_1(self):
        m = DensityMap(4, height_scale=1)
        m.add((-118.4680, 33.7419))
        m.add((-118.4677, 33.7418))
        m.add((-118.4675, 33.7417))
        m.add((-118.4672, 33.7415))
        self.assertListEqual([
            '+----+',
            '|999 |',
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


class TestTaster(TestCase):
    type_1_la = parse(["1452468552.938 !AIVDM,1,1,,B,14Wtnn002SGLde:BbrBmdTLF0Vql,0*6E"])[0]
    type_1_sf = parse(["!AIVDM,1,1,,A,15Mw0GP01SG?W>PE`laU<TJj0L20,0*67"])[0]
    type_5 = parse(["!WSVDM,2,1,0,A,5=JklSl00003UHDs:20l4E9<f04i@4U:22222217,0*4C",
                    "!WSVDM,2,2,0,A,05B0dl0HtS000000000000000000008,2*00"])[0]
    type_17 = parse(["!AIVDM,1,1,,A,Auju3sUbv8u`:JBCIf?vOeCSWmp:JOGeRN@?iD=I,0*61"])[0]

    def test_location_filtering(self):
        taster = Taster(lat=(32, 35))  # LA
        self.assertTrue(taster.likes(self.type_1_la))
        self.assertFalse(taster.likes(self.type_1_sf))

        taster = Taster(lon=(-121, -117))  # LA
        self.assertTrue(taster.likes(self.type_1_la))
        self.assertFalse(taster.likes(self.type_1_sf))

    def test_type_filtering(self):
        taster = Taster(sentence_type=[1])
        self.assertTrue(taster.likes(self.type_1_la))
        self.assertTrue(taster.likes(self.type_1_sf))
        self.assertFalse(taster.likes(self.type_5))
        self.assertFalse(taster.likes(self.type_17))

        taster = Taster(sentence_type=[5, 17])
        self.assertFalse(taster.likes(self.type_1_la))
        self.assertFalse(taster.likes(self.type_1_sf))
        self.assertTrue(taster.likes(self.type_5))
        self.assertTrue(taster.likes(self.type_17))

    def test_field_filtering(self):
        taster = Taster(field=['shiptype'])
        self.assertFalse(taster.likes(self.type_1_la))
        self.assertTrue(taster.likes(self.type_5))
        self.assertFalse(taster.likes(self.type_17))

    def test_packets_without_locations_are_rejected_when_filtering_for_location(self):
        taster = Taster(lat=(0, 90))
        self.assertFalse(taster.likes(self.type_5))

    def test_checksum_filter(self):
        good = parse("!AIVDM,1,1,,B,3;hw29cc6<<1qABsuhLN>=5ws`Qo,0*4C")
        bad = parse("!AIVDM,1,1,,B,3;hw29cc6<<1qABsuhLN>=5ws`Qo,0*4B")

        taster = Taster(checksum=None)
        self.assertTrue(taster.likes(good))
        self.assertTrue(taster.likes(bad))

        taster = Taster(checksum=True)
        self.assertTrue(taster.likes(good))
        self.assertFalse(taster.likes(bad))

        taster = Taster(checksum=False)
        self.assertFalse(taster.likes(good))
        self.assertTrue(taster.likes(bad))

    def test_invert_match(self):
        taster = Taster(lat=(32, 35), invert_match=True)  # LA
        self.assertFalse(taster.likes(self.type_1_la))
        self.assertTrue(taster.likes(self.type_1_sf))


from click.testing import CliRunner


class CommandLineSmokeTest(TestCase):
    commands = {cat, grep, as_text, burst, info, dump, stat}
    required_args = {stat: ['-f', 'type']}

    def test_handles_empty(self):
        for c in self.commands:
            runner = CliRunner()
            result = runner.invoke(c, self.args_for(c))
            self.assertEqual(0, result.exit_code, "for {}".format(c.name))

    def test_handles_one_line(self):
        for c in self.commands - {burst}:
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open('example.ais', 'w') as f:
                    f.write("1452468552.938 !AIVDM,1,1,,B,14Wtnn002SGLde:BbrBmdTLF0Vql,0*6E")
                result = runner.invoke(c, self.args_for(c, 'example.ais'))
                self.assertEqual(0, result.exit_code, "for {}".format(c.name))
                self.assertTrue(len(result.output) > 0, "for {}".format(c.name))

    def args_for(self, c, file='/dev/null'):
        if c in self.required_args:
            return self.required_args[c] + [file]
        else:
            return [file]
