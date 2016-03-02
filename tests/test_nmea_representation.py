from unittest import TestCase

from simpleais import *


class TestNmeaLump(TestCase):
    def test_bit_length(self):
        self.assertEqual(6, NmeaLump('1').bit_length())
        self.assertEqual(168, NmeaLump('402M45iv0c?NN0dST0TPK@7008Aq').bit_length())

    def test_type_int_aligned(self):
        l = NmeaLump('1', 0)
        self.assertEqual(Bits(1, 6), l.bit_range(0, 6))
        self.assertEqual(6, l.bit_length())

        l = NmeaLump('H', 0)
        self.assertEqual(Bits(24, 6), l.bit_range(0, 6))

    def test_type_int_unaligned(self):
        l = NmeaLump('402M45iv0c?NN0dST0TPK@7008Aq', 0)
        self.assertEqual(Bits(2016, 14), l.bit_range(38, 52))
        self.assertEqual(Bits(2, 4), l.bit_range(52, 56))
        self.assertEqual(Bits(22, 5), l.bit_range(56, 61))

    def test_bounds(self):
        l = NmeaLump('1', 0)
        self.assertRaises(ValueError, l.bit_range, -1, 0)
        self.assertRaises(ValueError, l.bit_range, 0, 7)
        self.assertRaises(ValueError, l.bit_range, 6, 6)
        self.assertRaises(ValueError, l.bit_range, 7, 100)


class TestNmeaPayload(TestCase):
    type_5 = NmeaPayload.join([
        NmeaPayload('53:Dbn02>i0KD8pG800<l60<Ln1@P4h5=<400017PQGFF4Dd0N33kQhQ@@j0', 0),
        NmeaPayload('00000000000', 2)])

    def test_basic_construction(self):
        body, fill_bits = '1', 0
        p = NmeaPayload(body, fill_bits)
        self.assertEqual(6, len(p))
        self.assertEqual(Bits(1, 6), p.bits)

    def test_padding(self):
        for fill_bits in range(0, 6):
            payload = NmeaPayload('w', fill_bits)
            self.assertEqual(Bits('111111')[0:(6 - fill_bits)], payload.bits,
                             msg='failure for {} fill bits'.format(fill_bits))

    def test_early_int(self):
        self.assertEqual(5, self.type_5.unsigned_int(0, 6))

    def test_later_int(self):
        p = NmeaPayload.join([
            NmeaPayload('1'),
            NmeaPayload('2')])
        self.assertEqual(2, p.unsigned_int(6, 12))

    def test_spans_lumps(self):
        p = NmeaPayload.join([
            NmeaPayload('1'),
            NmeaPayload('1')])
        self.assertEqual(65, p.unsigned_int(0, 12))

    def test_padding_shenanigans(self):
        p = NmeaPayload.join([
            NmeaPayload('3', 1),
            NmeaPayload('3', 1)])
        self.assertEqual(10, p.bit_length())
        self.assertEqual(33, p.unsigned_int(0, 10))
        self.assertEqual(Bits('0000100001'), p.bits)

    def test_full_message(self):
        body = '15NaEPPP01oR`R6CC?<j@gvr0<1C'
        p = NmeaPayload('%s' % body, 0)
        self.assertEqual(6 * len(body), len(p))
