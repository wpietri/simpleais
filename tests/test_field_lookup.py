from unittest import TestCase

import simpleais
from simpleais import *

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

    def test_raw_enums(self):
        l = ENUM_LOOKUPS['shiptype']
        self.assertEqual("Fishing", str(l[30]))
        self.assertEqual(30, int(l[30]))
        self.assertEqual("Other Type, no additional information", str(l[99]))
        self.assertEqual(99, int(l[99]))
        self.assertTrue(99 in l)
        self.assertFalse(100 in l)

    def test_decoder_decodes(self):
        d = MESSAGE_DECODERS[1]
        m = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        self.assertEqual('367678850', d.decode('mmsi', m))
        self.assertAlmostEqual(33.7302, d.decode('lat', m))
        self.assertAlmostEqual(-118.2634, d.decode('lon', m))

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
        # 3.3.7.2.2 and 3.3.7.3.2 in ITU-R M.1371-5 to interpret it fully.

    def test_known_and_unknown_fields(self):
        m = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        self.assertTrue(m['type'])
        self.assertFalse(m['unknown'])

    def test_type_17_location(self):
        # not sure where this example came from, so I'm not totally sure it's right, but it seems to work
        m = parse(['!AIVDM,2,1,2,B,AkklHKotBpj>Pv8OptkMaD`J4:iU74U5807A6AQaM`;,0*45',
                   '!AIVDM,2,2,2,B,wibCPG`kAfs:E0Dhp,0*73'])[0]
        self.assertEqual(m['lat'], 42.86)
        self.assertEqual(m['lon'], -6.3233)

    def test_type_5(self):
        m = parse(['!AIVDM,2,1,8,A,55Mw0BP00001L=WKC?98uT4j1=@580000000000t1@D5540Ht6?UDp4iSp=<,0*74',
                   '!AIVDM,2,2,8,A,@0000000000,2*5C'])[0]
        self.assertEqual("366985290", m['mmsi'])
        self.assertEqual("WCY6432", m['callsign'])
        self.assertEqual("ROYAL STAR", m['shipname'])
        self.assertEqual(">US SFO 41", m['destination'])
        self.assertEqual(10, m['to_bow'])
        self.assertEqual(20, m['to_stern'])
        self.assertEqual(5, m['to_port'])
        self.assertEqual(5, m['to_starboard'])
        self.assertEqual("Passenger, all ships of this type", str(m['shiptype']))
        self.assertEqual(60, int(m['shiptype']))

    def test_type_4(self):
        # Base stations offer a time and position reference; the time may be different
        # than the timestamp given to sentences when received.
        m = parse('!AIVDM,1,1,,B,402M45iv0c?NN0dST0TPK@7008Aq,0*7F')
        self.assertAlmostEqual(63.8000, m['lat'], 4)
        self.assertAlmostEqual(9.7333, m['lon'], 4)
        self.assertTrue(m.field('time').valid())
        self.assertEqual(calendar.timegm((2016, 2, 22, 15, 30, 30, 0)), m['time'])
        self.assertEqual(40, len(m.field('time').bits()))

    def test_type_4_with_no_time(self):
        m = parse('1456560000.378 !AIVDM,1,1,,A,4023?>0000Htt12LAnDRa`G00d3I,0*44')
        self.assertIsNone(m['time'])

    def test_type_4_with_bad_time(self):
        m = parse('1456614528.900 !AIVDM,1,1,,B,4r`r4cc2tMhKpNFJtl1>Egqo1<9l,0*2C')
        self.assertIsNone(m['time'])

    def test_type_27_location(self):
        m = parse('!AIVDM,1,1,,A,KCQ9r=hrFUnH7P00,0*41')
        self.assertEqual(m['lon'], -154.2017)
        self.assertEqual(m['lat'], 87.065)

# this test is a sign of a terrible design problem. TODO: maybe make enum collections responsible for defaulting?
class TestEnumLookup(TestCase):
    def test_shiptype(self):
        enum_decoder = self.decoder_for_enum(5, 'shiptype')

        decoded_30 = enum_decoder(self.fake_payload(30))
        self.assertEqual(30, decoded_30.key)
        self.assertEqual("Fishing", decoded_30.value)
        self.assertEqual("Fishing", str(decoded_30))

        decoded_101 = enum_decoder(self.fake_payload(101))
        self.assertEqual(101, decoded_101.key)
        self.assertEqual("enum-unknown-101", decoded_101.value)
        self.assertEqual("enum-unknown-101", str(decoded_101))

    def test_navigation_status(self):
        enum_decoder = self.decoder_for_enum(1, 'status')
        decoded_1 = enum_decoder(self.fake_payload(1))
        self.assertEqual(1, decoded_1.key)
        self.assertEqual("At anchor", decoded_1.value)
        self.assertEqual("At anchor", str(decoded_1))

    def decoder_for_enum(self, packet_type, field_name):
        return MESSAGE_DECODERS[packet_type].field(field_name)._appropriate_nmea_decoder('e', field_name)

    def fake_payload(self, payload_value):
        class FakePayload:
            def __init__(self, val):
                self.val = val

            def int_for_bit_range(self, i1, i2):
                return self.val

        payload = FakePayload(payload_value)
        return payload


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


class TestRenderAsDict(TestCase):
    def setUp(self):
        super().setUp()

    def test_type_1(self):
        text = '!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F'
        time = 12345.0
        sentence = parse(str(time) + ' ' + text)
        expected_dict = {'accuracy': True,
                         'course': 57.8,
                         'heading': 511,
                         'ignored-145': 0,
                         'lat': 33.7302,
                         'lon': -118.2634,
                         'maneuver': 'enum-0',
                         'mmsi': '367678850',
                         'radio': 49235,
                         'raim': False,
                         'repeat': 0,
                         'second': 29,
                         'speed': 0.1,
                         'status': AisEnum(0, 'Under way using engine'),
                         'text': [text],
                         'received_at': time,
                         'turn': -0.0021,
                         'type': 1,}
        self.assertDictEqual(expected_dict, sentence.as_dict())

    def test_type_4_time(self):
        text = "!AIVDM,1,1,,A,403Othiv0eW>jo@FfjEjH>?02<1u,0*72"
        time = 12345.0
        sentence = parse(str(time) + ' ' + text)

        # received_at is the sentence's time field, the receiver timetamp
        self.assertEqual(time, sentence.time)
        self.assertEqual(time, sentence.as_dict()['received_at'])

        # but type 4 packets contain their own notion of time
        self.assertEqual(1456557290, sentence.as_dict()['time'])

    def test_type_5(self):
        text = ['!AIVDM,2,1,8,A,55Mw0BP00001L=WKC?98uT4j1=@580000000000t1@D5540Ht6?UDp4iSp=<,0*74',
                '!AIVDM,2,2,8,A,@0000000000,2*5C']
        sentence = parse(text)[0]
        expected = {
            'type': 5,
            'ais_version': 0,
            'mmsi': '366985290',
            'month': 0,
            'day': 0,
            'hour': 24,
            'minute': 60,
            'shiptype': AisEnum(60, 'Passenger, all ships of this type'),
            'to_port': 5,
            'to_starboard': 5,
            'to_bow': 10,
            'to_stern': 20,
            'draught': 2.4,
            'shipname': 'ROYAL STAR',
            'callsign': 'WCY6432',
            'destination': '>US SFO 41',
            'text': text,
            'imo': 0,
            'repeat': 0,
            'epfd': 'enum-1',
            'ignored-423': 0,
            'dte': False}

        self.assertDictEqual(expected, sentence.as_dict())
