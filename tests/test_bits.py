from unittest import TestCase

from simpleais import *


class TestBits(TestCase):
    def test_empty(self):
        self.assertEqual('', str(Bits()))

    def test_zero(self):
        self.assertEqual('0', str(Bits(0)))

    def test_one(self):
        self.assertEqual('1', str(Bits(1)))

    def test_with_length(self):
        self.assertEqual('0001', str(Bits(1, 4)))

    def test_bits_from_bits(self):
        self.assertEqual(Bits('1'), Bits(Bits('1')))

    def test_bits_is_bits(self):
        self.assertEqual('1001', str(Bits('1001')))

    def test_length(self):
        self.assertEqual(0, len(Bits()))
        self.assertEqual(1, len(Bits('1')))
        self.assertEqual(4, len(Bits('1001')))

    def test_int_round_trip(self):
        self.assertEqual(12345, int(Bits(12345)))

    def test_join(self):
        buf = [Bits('100'), Bits('000'), Bits('001')]
        self.assertEqual(Bits('100000001'), Bits.join(buf))

    def test_add(self):
        result = Bits('100') + Bits('000') + Bits('001')
        self.assertEqual(Bits('100000001'), result)

    def test_append(self):
        buf = Bits()
        buf.append(Bits('100'))
        self.assertEqual(Bits('100'), buf)
        buf.append(Bits('000'))
        self.assertEqual(Bits('100000'), buf)
        buf.append(Bits('001'))
        self.assertEqual(Bits('100000001'), buf)

    def test_extract_single_bits(self):
        bits = Bits("00011011")
        self.assertEqual(Bits('0'), Bits('0')[0])
        self.assertEqual(Bits('1'), Bits('1')[0])

        self.assertEqual(Bits('1'), Bits('10')[0])
        self.assertEqual(Bits('0'), Bits('10')[1])

        self.assertEqual(Bits('1'), Bits('101')[0])
        self.assertEqual(Bits('1'), Bits('101')[2])

    def test_extract_ranges(self):
        bits = Bits("00011011")
        self.assertEqual(Bits('00'), bits[0:2])
        self.assertEqual(Bits('0001'), bits[0:4])
        self.assertEqual(Bits('000110'), bits[0:6])
        self.assertEqual(Bits('1011'), bits[4:8])

    def test_invalid_range(self):
        bits = Bits("00011011")
        self.assertEqual(Bits('11'), bits[6:25])
        self.assertEqual(Bits(0, 0), bits[20:25])
