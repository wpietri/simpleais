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
        "description": "Message Type",
        "member": "type",
        "type": "u"
      },
      {
        "start": 6,
        "end": 7,
        "description": "Repeat Indicator",
        "member": "repeat",
        "type": "u"
      }
    ]
  }
}'''


class TestFieldLookup(TestCase):
    def test_decoder_creation(self):
        d = MessageDecoder(json.loads(field_json)["1"])
        self.assertEqual(slice(0, 6), d.bit_range('type'))

    def test_loaded_decoders(self):
        d = MESSAGE_DECODERS[1]
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
        d = MESSAGE_DECODERS[1]
        m = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        self.assertEqual('367678850', d.decode('mmsi', m.payload.bits))
        self.assertAlmostEquals(33.7302, d.decode('lat', m.payload.bits))
        self.assertAlmostEquals(-118.2634, d.decode('lon', m.payload.bits))

    def test_fields_for_sentence(self):
        m = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        self.assertEqual(16, len(m.fields()))
        self.assertEqual("Message Type", m.fields()[0].description())
        self.assertEqual("Message Type", m.field('type').description())

        message_type = m.field(0)
        self.assertEqual("type", message_type.name())
        self.assertEqual("Message Type", message_type.description())
        self.assertEqual(1, message_type.value())
        self.assertEqual(Bits('000001'), message_type.bits())

        raim = m.field(14)
        self.assertEqual("raim", raim.name())
        self.assertEqual("RAIM flag", raim.description())
        self.assertEqual(False, raim.value())
        self.assertEqual(Bits('0'), raim.bits())

        radio_status = m.field(15)
        self.assertEqual("radio", radio_status.name())
        self.assertEqual("Radio status", radio_status.description())
        self.assertEqual(49235, radio_status.value())
        self.assertEqual(Bits('0001100000001010011'), radio_status.bits())

        # NB: Radio status is actually way more complicated than this. See
        # 3.3.7.2.2 and 3.3.7.3.2 in ITU-R M.1371-5 if you'd like to
        # interpret it fully.

    def test_known_and_unknown_fields(self):
        m = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        self.assertTrue(m['type'])
        self.assertFalse(m['unknown'])


class TestNettlesomePackets(TestCase):
    def test_type_7(self):
        """
        Type 7 packets are variable length. This particular type 7 packet ends
        in the middle of a field, suggesting a poorly implemented sender, or
        some different use of the remaining bits.
        """
        m = parse("1452468619.999 !AIVDM,1,1,,A,75gR`rBPLlNtuiugkkAiQ<3bw0,4*52")
        self.assertTrue(m.field('mmsi3').valid())
        self.assertTrue(m.field('mmsiseq3').valid())
        self.assertFalse(m.field('mmsi4').valid())
        self.assertFalse(m.field('mmsiseq4').valid())
