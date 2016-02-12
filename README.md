
SimpleAIS
=========

I needed a simple AIS decoder for a small art project. I couldn't find one, so
I'm making something minimally adequate for my needs. Decoders are generated
automatically from public protocol documentation, but since I use few of
the fields myself, I haven't verified much of the decoding. This code is
rough and doesn't worry much about correctness, and so shouldn't be used for
anything that matters. It especially shouldn't be used for ship navigation.

SimpleAIS also provides some handy command-line tools, including:

* aisgrep - pulls out sentences matching given criteria
* aist - a text dump of sentences, one per line
* aisburst - takes a large file of sentences and splits it into one file per sender
* aisinfo - give summary reports for a file of sentences with optional details on each sender
* aisdump - detailed dumps of individual sentences, including bits

If you would like to try it out and don't have any AIS data handy, try
tests/sample.ais.

Contributions welcome.

## Library usage

Here's an example, a simplified version of the `aist` tool, which prints
one line per complete AIS message:


    for sentence in sentences_from_sources(sources):
        result = []
        if sentence.time:
            result.append(sentence.time.strftime(TIME_FORMAT))
        result.append("{:2}".format(sentence.type_id()))
        result.append("{:9}".format(str(sentence['mmsi'])))
        location = sentence.location()
        if location:
            result.append("{:9.4f} {:9.4f}".format(location[0], location[1]))
        if sentence.type_id() == 5:
            result.append("{}->{}".format(sentence['shipname'], sentence['destination']))

        print(" ".join(result))

The `sentence_from_sources()` function will pull from a wide variety of sources
(local files, serial ports, HTTP URLs), yielding only complete sentences as they
arrive. Each sentence has a wide variety of readable information. Documented
fields can all be referred to by name. For example, `sentence['mmsi']` or
`sentence['shipname']`. The `location()` method will return a tuple of the
form `(longitude, latitude)`. Missing or invalid fields will return `None`.


## Command-line usage

Suppose you have a file with a bunch of AIS data from the San Francisco
area. You'd like to pull out location transmissions from various sorts
of ships and then plot a map of signal density. Further, you'd like
to mark the locations of Fort Point and Fort Mason with asterisks
just so you have some idea of what you're seeing. To do that, you can
use aisgrep to get the relevant packets and aisinfo to plot the map:

    $ aisgrep -t 1 -t 2 -t 3 -t 5 -t 18 -t 19 bayarea.ais | \
    aisinfo --map --point -122.4775 37.8108 --point -122.4321 37.8065
    
    Found 51 senders in 15419 good sentences with 39 invalid (0.25%).
          top left: -122.9261, 37.9233
      bottom right: -122.3013, 37.5967
             width: 55.06 km
            height: 36.33 km
    +------------------------------------------------------------+
    |                                            .   .           |
    |                                                 .          |
    |                                             . . ..         |
    |                                         ..1... ....        |
    |                                           ...........      |
    |                                          ......1... ..     |
    |                                       ....*..1*19.....     |
    |        .                          ......          . ..    .|
    |              .....          .......                        |
    |                   . .........                              |
    |                       ...                                  |
    |                    ... .                                   |
    |                 ....  .                                    |
    |                ..     .                                    |
    |                       .                                    |
    |          ..                                                |
    |                                                            |
    |                                                            |
    |.                                                           |
    +------------------------------------------------------------+


## Sources

My main source for protocol information is here: http://catb.org/gpsd/AIVDM.html

More protocol info is here: http://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1371-5-201402-I!!PDF-E.pdf

The protocol checksum is here: https://en.wikipedia.org/wiki/NMEA_0183

