from unittest import TestCase

from simpleais import *
import simpleais


class TestBasicParsing(TestCase):
    def test_convenience_parse(self):
        self.assertEqual(None, simpleais.parse(''))
        self.assertEqual([], simpleais.parse([]))

    def test_empty(self):
        self.assertEqual(None, simpleais.parse_one(''))

    def test_basic_sentence(self):
        sentence = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        self.assertEqual(Talker('AB'), sentence.talker)
        self.assertEqual(SentenceType('VDM'), sentence.sentence_type)
        # TODO: above is text, but don't I want meaning?

    def test_basic_lists(self):
        sentences = simpleais.parse([
            '!AIVDM,1,1,,B,H52R9E1<D<tpB1LTp@000000000,2*5C',
            '!ABVDM,1,1,,A,15MqdBP001GRT>>CCUu360Lr041d,0*69'
        ])
        self.assertEqual(2, len(sentences))

    def test_fragment_assembly(self):
        sentence = simpleais.parse([
            '!AIVDM,3,1,3,A,85NoHR1KfI99t:BHBI3sWpAoS7VHRblW8McQtR3lsFR,0*5A',
            '!AIVDM,3,2,3,A,ApU6wWmdIeJG7p1uUhk8Tp@SVV6D=sTKh1O4fBvUcaN,0*5E',
            '!AIVDM,3,3,3,A,j;lM8vfK0,2*34'
        ])
        self.assertEqual(1, len(sentence))


class TestFragmentPool(TestCase):
    def __init__(self, method_name='runTest'):
        super(TestFragmentPool, self).__init__(method_name)
        self.raw_fragments = [
            '!AIVDM,3,1,3,A,85NoHR1KfI99t:BHBI3sWpAoS7VHRblW8McQtR3lsFR,0*5A',
            '!AIVDM,3,2,3,A,ApU6wWmdIeJG7p1uUhk8Tp@SVV6D=sTKh1O4fBvUcaN,0*5E',
            '!AIVDM,3,3,3,A,j;lM8vfK0,2*34'
        ]

        self.cooked_fragments = [parse_one(m) for m in self.raw_fragments]

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
        sentence = f.pop_full_sentence()
