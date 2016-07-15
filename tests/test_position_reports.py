from unittest import TestCase

import simpleais


class TestPositionReports(TestCase):

    def setUp(self):
        super().setUp()

    def test_basics(self):
        m = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        self.assertEqual(1, m.type_id())
        self.assertEqual('367678850', m['mmsi'])
        self.assertAlmostEquals(-118.2634, m['lon'])
        self.assertAlmostEquals(33.7302, m['lat'])

    def test_as_location(self):
        m = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        location = m.location()
        self.assertAlmostEquals(-118.2634, location[0])
        self.assertAlmostEquals(33.7302, location[1])

    def test_bad_values(self):
        # packet expresses longitude of 221.8539, which is crazy, so no location should be available
        m = simpleais.parse('!AIVDM,1,1,,A,2C2ILGC4oRgoT?r1fdC3wcvi26;8,0*33')
        self.assertEqual('203840605', m['mmsi'])
        self.assertIsNone(m['lon'])
        self.assertAlmostEquals(3.0226, m['lat'])
        self.assertIsNone(m.location())

        # packet is too short, so no location should be available
        m = simpleais.parse('1452655664.394 !AIVDM,1,1,,A,ECgb9OI9R@106jh`8@7Q3wmTkP06,0*3A')
        self.assertEqual('251300221', m['mmsi'])
        self.assertIsNone(m['lon'])
        self.assertIsNone(m['lat'])
        self.assertIsNone(m.location())

    def test_no_lat_or_lon(self):
        m = simpleais.parse('!ABVDM,1,1,,A,152MQ1qP?w<tSF0l4Q@>4?wp1p7G,0*78')
        self.assertEqual('338125063', m['mmsi'])
        self.assertIsNone(m['lon'])
        self.assertIsNone(m['lat'])

    def test_has_speed(self):
        m = simpleais.parse('!AIVDM,1,1,,B,19NSH1P02QG?:MjE`?qBFApb0>`<,0*41')
        self.assertTrue('speed' in m)
        self.assertEqual(16.1, m['speed'])

    def test_has_zero_speed(self):
        m = simpleais.parse('!AIVDM,1,1,,A,39NSH1U000GND`LCRQc;WpM`P>`<,0*6C')
        self.assertTrue('speed' in m)
        self.assertEqual(0, m['speed'])
