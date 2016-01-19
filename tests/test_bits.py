from unittest import TestCase

from simpleais import *


class TestBasicParsing(TestCase):
    def test_empty(self):
        self.assertEqual('', Bits().contents)

    def test_zero(self):
        self.assertEqual('0', Bits(0).contents)

    def test_one(self):
        self.assertEqual('1', Bits(1).contents)

    def test_with_length(self):
        self.assertEqual('0001', Bits(1, 4).contents)

    def test_bits_is_bits(self):
        self.assertEqual('1001', Bits('1001').contents)

    def test_int_round_trip(self):
        self.assertEqual(12345, int(Bits(12345)))

    def test_join(self):
        buf = [Bits('100'), Bits('000'), Bits('001')]
        self.assertEqual(Bits('100000001'), Bits.join(buf))
