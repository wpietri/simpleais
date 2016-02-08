from unittest import TestCase

from simpleais import *
import simpleais

field_json = '''{
  "1": {
    "name": "Position Report Class A",
    "fields": [
      {
        "start": 0,
        "end": 5,
        "len": 6,
        "description": "Message Type",
        "member": "type",
        "t": "u",
        "units": "Constant: 1"
      },
      {
        "start": 6,
        "end": 7,
        "len": 2,
        "description": "Repeat Indicator",
        "member": "repeat",
        "t": "u",
        "units": "Message repeat count"
      }
    ]
  }
}'''


class TestFieldLookup(TestCase):
    def test_decoder_creation(self):
        d = Decoder(json.loads(field_json)["1"])
        self.assertEqual(slice(0, 6), d.bit_range('type'))

    def test_loaded_decoders(self):
        d = DECODERS[1]
        self.assertEqual(slice(0, 6), d.bit_range('type'))
        self.assertEqual(slice(6, 8), d.bit_range('repeat'))
        self.assertEqual(slice(8, 38), d.bit_range('mmsi'))
        self.assertEqual(slice(38, 42), d.bit_range('status'))
        self.assertEqual(slice(42, 50), d.bit_range('turn'))
        self.assertEqual(slice(50, 60), d.bit_range('speed'))
        self.assertEqual(slice(60, 61), d.bit_range('accuracy'))
        self.assertEqual(slice(61, 89), d.bit_range('lon'))
        self.assertEqual(slice(89, 116), d.bit_range('lat'))
        self.assertEqual(slice(116, 128), d.bit_range('course'))
        self.assertEqual(slice(128, 137), d.bit_range('heading'))
        self.assertEqual(slice(137, 143), d.bit_range('second'))
        self.assertEqual(slice(143, 145), d.bit_range('maneuver'))
        self.assertEqual(slice(148, 149), d.bit_range('raim'))
        self.assertEqual(slice(149, 168), d.bit_range('radio'))

    def test_decoder_decodes(self):
        d = DECODERS[1]
        m = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        self.assertEqual('367678850', d.decode('mmsi', m.payload.bits))
        self.assertAlmostEquals(33.7302, d.decode('lat', m.payload.bits))
        self.assertAlmostEquals(-118.2634, d.decode('lon', m.payload.bits))
