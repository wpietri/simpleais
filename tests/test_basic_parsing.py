from unittest import TestCase

from simpleais import *
import simpleais

fragmented_message_type_8 = ['!AIVDM,3,1,3,A,85NoHR1KfI99t:BHBI3sWpAoS7VHRblW8McQtR3lsFR,0*5A',
                             '!AIVDM,3,2,3,A,ApU6wWmdIeJG7p1uUhk8Tp@SVV6D=sTKh1O4fBvUcaN,0*5E',
                             '!AIVDM,3,3,3,A,j;lM8vfK0,2*34']


class TestBasicParsing(TestCase):
    def test_convenience_parse(self):
        self.assertEqual(None, simpleais.parse(''))
        self.assertEqual([], simpleais.parse([]))

    def test_empty(self):
        self.assertEqual(None, simpleais.parse_one(''))

    def test_basic_sentence(self):
        sentence = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        self.assertIsInstance(sentence, Sentence)
        self.assertEqual('AB', sentence.talker)
        self.assertEqual('VDM', sentence.sentence_type)
        self.assertEqual('A', sentence.radio_channel)
        self.assertEqual(1, sentence.type_id())

    def test_single_fragment(self):
        body = '85NoHR1KfI99t:BHBI3sWpAoS7VHRblW8McQtR3lsFR'
        padding = 0
        fragment = simpleais.parse('!AIVDM,3,1,3,A,%s,%s*5A' % (body, padding))
        self.assertIsInstance(fragment, SentenceFragment)
        self.assertEqual(len(body) * 6 - padding, len(fragment.bits()))

    def test_basic_lists(self):
        sentences = simpleais.parse([
            '!AIVDM,1,1,,B,H52R9E1<D<tpB1LTp@000000000,2*5C',
            '!ABVDM,1,1,,A,15MqdBP001GRT>>CCUu360Lr041d,0*69'
        ])
        self.assertEqual(2, len(sentences))

    def test_optional_date(self):
        text = "1454124838.633\t!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F"
        sentence = simpleais.parse(text)
        self.assertEqual(datetime.fromtimestamp(1454124838.633), sentence.time)

    def test_fragment_assembly(self):
        raw = fragmented_message_type_8
        sentences = simpleais.parse(raw)
        self.assertEqual(1, len(sentences))
        message_bytes = sum([len(m) - len('!AIVDM,3,1,3,A,') - len(',2*34') for m in raw])
        message_bits = message_bytes * 6 - 2  # where 2 is padding on last fragment
        self.assertEquals(message_bits, len(sentences[0].message_bits()))

    def test_round_trip_for_single_fragment(self):
        text = '!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F'
        sentence = simpleais.parse(text)
        self.assertEqual(text, sentence.text[0])

    def test_round_trip_for_multiple_fragments(self):
        sentence = simpleais.parse(fragmented_message_type_8)[0]
        self.assertEqual(fragmented_message_type_8, sentence.text)

    def test_checksum_validation_for_single_fragment_sentences(self):
        good = parse("!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F")
        self.assertTrue(good.check())
        bad = parse("!AIVDM,1,1,,A,ENkb9I99S@:9h4W17bW2@I7@@@;V4=v:nv;h00003vP000,2*15")
        self.assertFalse(bad.check())

    def test_checksum_validation_for_multiple_fragment_sentences(self):
        good_and_bad_1 = parse("!AIVDM,2,1,6,B,55NEA8T00001L@GC7WT4h<5A85b0<hU10E:2000t1@`56t0Ht04hC`1TPCPj,0*10")
        good_and_bad_2 = parse("!AIVDM,2,2,6,B,Dhkh0000000,2*0F")
        self.assertTrue(good_and_bad_1.check())
        self.assertFalse(good_and_bad_2.check())
        good_and_bad = Sentence.from_fragments([good_and_bad_1, good_and_bad_2])
        self.assertFalse(good_and_bad.check())
        self.assertEqual([True, False], good_and_bad.checksum_valid)


class TestFragment(TestCase):
    def test_last(self):
        frags = [parse(f) for f in fragmented_message_type_8]
        self.assertFalse(frags[0].last())
        self.assertFalse(frags[1].last())
        self.assertTrue(frags[2].last())

    def test_follows(self):
        frags = [parse(f) for f in fragmented_message_type_8]
        self.assertTrue(frags[1].follows(frags[0]))
        self.assertTrue(frags[2].follows(frags[1]))
        self.assertFalse(frags[2].follows(frags[0]))
        self.assertFalse(frags[0].follows(frags[2]))

    def test_follows_for_different_messages(self):
        frags = [parse(f) for f in ['!AIVDM,2,1,8,A,55NJ<1000001L@K;KS0=9U=@4j0TV2222222220U1p?456t007ThC`12,0*40',
                                    '!AIVDM,2,2,8,A,AAkp88888888880,2*37',
                                    '!AIVDM,2,1,4,B,54hB6<42CMBq`LAOB20EIHUH622222222222220U30J,0*1B',
                                    '!AIVDM,2,2,4,B,5540Ht64kkAEj1DQH4mCSVH88880,2*4C']]
        self.assertTrue(frags[1].follows(frags[0]))
        self.assertTrue(frags[3].follows(frags[2]))
        self.assertFalse(frags[2].follows(frags[0]))
        self.assertFalse(frags[3].follows(frags[0]))


class TestStreamParser(TestCase):
    def test_simple_use(self):
        p = StreamParser()
        self.assertFalse(p.has_sentence())
        p.add('!ABVDM,1,1,,A,15MqdBP001GRT>>CCUu360Lr041d,0*69')
        self.assertTrue(p.has_sentence())
        self.assertEqual(1, p.next_sentence().type_id())
        self.assertFalse(p.has_sentence())

    def test_buffer_results(self):
        p = StreamParser()
        self.assertFalse(p.has_sentence())
        p.add('!ABVDM,1,1,,A,15MqdBP001GRT>>CCUu360Lr041d,0*69')
        p.add('!ABVDM,1,1,,B,35NF6IPOiEoRe@HCBOS0VPeF0P00,0*54')
        self.assertTrue(p.has_sentence())
        self.assertEqual(1, p.next_sentence().type_id())
        self.assertEqual(3, p.next_sentence().type_id())
        self.assertFalse(p.has_sentence())

    def test_fragment_assembly(self):
        p = StreamParser()
        i = iter(fragmented_message_type_8)
        self.assertFalse(p.has_sentence())
        p.add(next(i))
        self.assertFalse(p.has_sentence())
        p.add(next(i))
        self.assertFalse(p.has_sentence())
        p.add(next(i))
        self.assertTrue(p.has_sentence())
        self.assertEqual(8, p.next_sentence().type_id())
        self.assertFalse(p.has_sentence())

    def test_partial_sentence_yields_nothing(self):
        p = StreamParser()
        p.add('!ABVDM,2,1,8,B,55NV>k000001L@SGCC4Dp@D5Hu800000000000001PF5300Ht023kA@00000,0*33')
        self.assertFalse(p.has_sentence())

        p = StreamParser()
        p.add('!AIVDM,2,2,6,A,00000000000,2*22')
        self.assertFalse(p.has_sentence())

class TestFragmentPool(TestCase):
    def __init__(self, method_name='runTest'):
        super(TestFragmentPool, self).__init__(method_name)
        self.raw_fragments = fragmented_message_type_8

        self.cooked_fragments = self.parse_fragments_separately(self.raw_fragments)

    def parse_fragments_separately(self, fragments):
        return [parse_one(m) for m in fragments]

    def test_empty(self):
        f = FragmentPool()
        self.assertFalse(f.has_full_sentence())
        with self.assertRaises(ValueError):
            f.pop_full_sentence()

    def test_partial_fill(self):
        f = FragmentPool()
        f.add(self.cooked_fragments[0])
        f.add(self.cooked_fragments[1])
        self.assertFalse(f.has_full_sentence())
        with self.assertRaises(Exception):
            f.pop_full_sentence()

    def test_normal_usage(self):
        f = FragmentPool()
        f.add(self.cooked_fragments[0])
        f.add(self.cooked_fragments[1])
        f.add(self.cooked_fragments[2])
        self.assertTrue(f.has_full_sentence())
        f.pop_full_sentence()

    def test_leftovers_dont_harm_results(self):
        fragments = self.parse_fragments_separately(
            ['!ABVDM,2,1,2,A,55NJ<1000001L@K;KS0=9U=@4j0TV2222222220U1p?456t007ThC`12AAkp,0*5A',
             '!AIVDM,2,1,8,A,55NJ<1000001L@K;KS0=9U=@4j0TV2222222220U1p?456t007ThC`12,0*40',
             '!AIVDM,2,2,8,A,AAkp88888888880,2*37',
             '!AIVDM,2,1,4,B,54hB6<42CMBq`LAOB20EIHUH622222222222220U30J,0*1B',
             '!AIVDM,2,2,4,B,5540Ht64kkAEj1DQH4mCSVH88880,2*4C'])
        f = FragmentPool()
        f.add(fragments[0])
        self.assertFalse(f.has_full_sentence())
        f.add(fragments[1])
        self.assertFalse(f.has_full_sentence())
        f.add(fragments[2])
        self.assertTrue(f.has_full_sentence())
        f.pop_full_sentence()
        self.assertFalse(f.has_full_sentence())
        f.add(fragments[3])
        self.assertFalse(f.has_full_sentence())
        f.add(fragments[4])
        self.assertTrue(f.has_full_sentence())
        f.pop_full_sentence()

    def test_trailing_fragment(self):
        f = FragmentPool()
        f.add(parse('!AIVDM,2,2,6,A,00000000000,2*22'))
        self.assertFalse(f.has_full_sentence())


class TestNmeaPayload(TestCase):
    def test_basic_construction(self):
        body, fill_bits = '1', 0
        p = NmeaPayload(body, fill_bits)
        self.assertEqual(6, len(p))
        self.assertEqual(Bits(1, 6), p.bits)

    def test_construction_from_bits(self):
        p = NmeaPayload(Bits('000001'))
        self.assertEqual(6, len(p))
        self.assertEqual('000001', str(p.bits))

    def test_padding(self):
        for fill_bits in range(0, 6):
            payload = NmeaPayload('w', fill_bits)
            self.assertEqual(Bits('111111')[0:(6 - fill_bits)], payload.bits,
                             msg='failure for {} fill bits'.format(fill_bits))

    def test_full_message(self):
        body = '15NaEPPP01oR`R6CC?<j@gvr0<1C'
        p = NmeaPayload('%s' % body, 0)
        self.assertEqual(6 * len(body), len(p))


class TestNameParsing(TestCase):
    def test_normal_name(self):
        m = parse(['!AIVDM,2,1,0,B,55QEQ`42Cktc<IL?J20@tpNl61A8U@tr2222221@BhQ,0*45',
                   '!AIVDM,2,2,0,B,H86tl0PDSlhDRE3p3F8888888880,2*57'])[0]
        self.assertEqual('DONG-A TRITON', m['shipname'])

    def test_strange_name(self):
        m = parse(['!AIVDM,2,1,7,B,54`Ut;l2CO<P?H53<010DL5=E>1HuT4LE800001@LHi,0*12',
                   '!AIVDM,2,2,7,B,JF6uF0G1H40C0000000000000000,2*50'])[0]
        self.assertEqual('PEGASUS VOYAGER', m['shipname'])
