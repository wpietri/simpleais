from unittest import TestCase

from simpleais import *
import simpleais


class TestPositionReports(TestCase):
    """
    //: Type CNB
    .Common Navigation Block
    [frame="topbot",options="header"]
    |==============================================================================
    |Field   |Len |Description             |Member    |T|Units
    |0-5     | 6  |Message Type            |type      |u|Constant: 1-3
    |6-7     | 2  |Repeat Indicator        |repeat    |u|Message repeat count
    |8-37    |30  |MMSI                    |mmsi      |u|9 decimal digits
    |38-41   | 4  |Navigation Status       |status    |e|See "Navigation Status"
    |42-49   | 8  |Rate of Turn (ROT)      |turn      |I3|See below
    |50-59   |10  |Speed Over Ground (SOG) |speed     |U1|See below
    |60-60   | 1  |Position Accuracy       |accuracy  |b|See below
    |61-88   |28  |Longitude               |lon       |I4|Minutes/10000 (see below)
    |89-115  |27  |Latitude                |lat       |I4|Minutes/10000 (see below)
    |116-127 |12  |Course Over Ground (COG)|course    |U1|Relative to true north,
                                                         to 0.1 degree precision
    |128-136 | 9  |True Heading (HDG)      |heading   |u|0 to 359 degrees,
                                                          511 = not available.
    |137-142 | 6  |Time Stamp              |second    |u|Second of UTC timestamp
    |143-144 | 2  |Maneuver Indicator      |maneuver  |e|See "Maneuver Indicator"
    |145-147 | 3  |Spare                   |          |x|Not used
    |148-148 | 1  |RAIM flag               |raim      |b|See below
    |149-167 |19  |Radio status            |radio     |u|See below
    |==============================================================================
    """

    def setUp(self):
        super().setUp()

    def test_basics(self):
        m = simpleais.parse('!ABVDM,1,1,,A,15NaEPPP01oR`R6CC?<j@gvr0<1C,0*1F')
        self.assertEqual(1, m.type_id())
        self.assertEqual('367678850', m['mmsi'])
        self.assertAlmostEquals(33.7302, m['lat'])
        self.assertAlmostEquals(-118.2634, m['lon'])
