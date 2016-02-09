
SimpleAIS
=========

I needed a simple AIS decoder for a small art project. I couldn't find one,
so I'm making something minimally adequate for my needs. This code is quite
rough, and so shouldn't be used for anything that matters. It especially
shouldn't be used for ship navigation. Decoders are generated automatically
from public protocol documentation, but since I use few of the fields
myself, I haven't verified much of the decoding.

SimpleAIS also provides some handy command-line tools, including:

* aisgrep - pulls out sentences matching given criteria
* aist - a text dump of sentences, one per line
* aisburst - takes a large file of sentences and splits it into one file per sender
* aisinfo - give summary reports for a file of sentences with optional details on each sender
* aisdump - detailed dumps of individual sentences, including bits

If you would like to try it out and don't have any AIS data handy, try
tests/sample.ais.

Contributions welcome.


### Sources

My main source for protocol information is here: http://catb.org/gpsd/AIVDM.html

The protocol checksum is here: https://en.wikipedia.org/wiki/NMEA_0183
