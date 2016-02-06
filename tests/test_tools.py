from unittest import TestCase

from simpleais.tools import DensityMap


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
        """ Slightly weird, might be better in the middle"""
        m = DensityMap(3, 3)
        m.add(0, 0)
        self.assertListEqual([
            '+---+',
            '|   |',
            '|   |',
            '|9  |',
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
            '|   |',
            '|999|',
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
        m.add(33.7419,-118.4680)
        m.add(33.7418,-118.4677)
        m.add(33.7417,-118.4675)
        m.add(33.7415,-118.4672)
        self.assertListEqual([
            '+----+',
            '|9   |',
            '| 9  |',
            '|  9 |',
            '|   9|',
            '+----+',
        ], m.to_text())

