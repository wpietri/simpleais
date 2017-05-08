from unittest import TestCase

from simpleais import *


class TestBasicParsing(TestCase):
    def testBasics(self):
        m = parse('!AIVDM,1,1,,A,13bjvT?0000BSS8MN2`V3Whr0>`<,0*60')
        json_text = m.as_json()
        self.assertRegex(json_text, '"lon": 4\\.0535')
        self.assertEqual(4.0535, json.loads(json_text)['lon'])

    def testEnum(self):
        m = parse(["!AIVDM,2,1,8,B,55N5iuT00001L@?W33I=0U8UB0tJ1L5<PTpM@tp620O66u8=N5EhDj7i0h00,0*34",
                   "!AIVDM,2,2,8,B,00000000000,2*2F"])[0]
        j = json.loads(m.as_json())
        self.assertDictEqual({"enum_value": "Reserved for future use", "enum_id": 6}, j['shiptype'])

    def testBits(self):
        m = parse(["!AIVDM,2,1,3,A,A@2bBWjeoU`uP0@0eL9@DOpl061C00l025wwT@1@:Orl07i1vQL03ngn801d,0*09",
                   "!AIVDM,2,2,3,A,=h0505`SwpH0FTH21h0u=gl702h0,0*23"])[0]
        j = json.loads(m.as_json())
        self.assertEqual(17, j['type'])
        self.assertEqual(
            '0000010000000000101101011100001001010000010100011111111000110100000000000110000001010011000000000000' +
            '1101000000000000100001011111111111111001000100000000010100000010100111111110101101000000000001111100' +
            '0100000111111010000101110000000000001111011010111111011000100000000000000110110000110111000000000000' +
            '0101000000000101101000100011111111111000011000000000010110100100011000000010000001110000000000111101' +
            '001101101111110100000111000000000010110000000000',
            j['data'])
