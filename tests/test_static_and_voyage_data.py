from unittest import TestCase

from simpleais import *
import simpleais


class TestPositionReports(TestCase):
    """
//: Type 5
[frame="topbot",options="header"]
|==============================================================================
|Field   |Len |Description            |Member/Type  |T|Encoding
|0-5     |  6 |Message Type           |type         |u|Constant: 5
|6-7     |  2 |Repeat Indicator       |repeat       |u|Message repeat count
|8-37    | 30 |MMSI                   |mmsi         |u|9 digits
|38-39   |  2 |AIS Version            |ais_version  |u|0=<<ITU1371>>,
                                                       1-3 = future editions
|40-69   | 30 |IMO Number             |imo          |u|IMO ship ID number
|70-111  | 42 |Call Sign              |callsign     |t|7 six-bit characters
|112-231 |120 |Vessel Name            |shipname     |t|20 six-bit characters
|232-239 |  8 |Ship Type              |shiptype     |e|See "Codes for Ship Type"
|240-248 |  9 |Dimension to Bow       |to_bow       |u|Meters
|249-257 |  9 |Dimension to Stern     |to_stern     |u|Meters
|258-263 |  6 |Dimension to Port      |to_port      |u|Meters
|264-269 |  6 |Dimension to Starboard |to_starboard |u|Meters
|270-273 |  4 |Position Fix Type      |epfd         |e|See "EPFD Fix Types"
|274-277 |  4 |ETA month (UTC)        |month        |u|1-12, 0=N/A (default)
|278-282 |  5 |ETA day (UTC)          |day          |u|1-31, 0=N/A (default)
|283-287 |  5 |ETA hour (UTC)         |hour         |u|0-23, 24=N/A (default)
|288-293 |  6 |ETA minute (UTC)       |minute       |u|0-59, 60=N/A (default)
|294-301 |  8 |Draught                |draught      |U1|Meters/10
|302-421 |120 |Destination            |destination  |t|20 6-bit characters
|422-422 |  1 |DTE                    |dte          |b|0=Data terminal ready,
                                                       1=Not ready (default).
|423-423 |  1 |Spare                  |             |x|Not used    """

    def setUp(self):
        super().setUp()

    def test_basics(self):
        m = simpleais.parse(['!AIVDM,2,1,0,B,55QEQ`42Cktc<IL?J20@tpNl61A8U@tr2222221@BhQ,0*45',
        '!AIVDM,2,2,0,B,H86tl0PDSlhDRE3p3F8888888880,2*57'])[0]
        self.assertEqual(5, m.type_id())
        self.assertEqual('370500000', m['mmsi'])
        self.assertEqual('DONG-A TRITON', m['shipname'])
        self.assertEqual('ROSARITO MX', m['destination'])

