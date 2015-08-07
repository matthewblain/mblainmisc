#!/usr/bin/env python
"""kml2postgis 'conversion' tool.

Converts some KML exported from basecamp into 'insert' statements suitable
for CartoDB.
This is probably generic for any similar KML and for any PostGIS database,
but it's initially just for this specific use case.
It assumes the table has a column named 'name' and 'the_geom'.

This could also surely be improved by picking a KML library and using it.

This could be improved by connecting directly to cartodb or other dbs.

This is NOT safe against SQL injection., so use it only on known input.
"""

__author__ = 'Matthew Blain'

import argparse
import sys
from xml.dom import minidom

KMLNS = 'http://www.opengis.net/kml/2.2'


def TracksFromKml(kmlFile):
    """Return a list of dicts representing each named LineString found."""
    dom = minidom.parse(kmlFile)

    # This is horrid: We simply find all the LineString elements,
    # then find the name in the surrounding folder, and return that.
    results = []
    lineStrings = dom.getElementsByTagNameNS(KMLNS, 'LineString')
    for lineString in lineStrings:
        r = {}
        enclosing = lineString.parentNode.parentNode
        name = enclosing.getElementsByTagNameNS(KMLNS, 'name')
        if name:
            r['name'] = name[0].firstChild.nodeValue
        else:
            r['name'] = ''  # Or leave it missing?
        r['fragment'] = lineString.toxml()
        results.append(r)

    return results


def InsertsFromTracks(tableName, tracks):
    """Return a list of INSERT statements.

  Args:
    tableName: The name of the SQL table to use.
    tracks: List of dicts with name/kml geogfragments.
  """
    results = []
    for track in tracks:
        statement = 'INSERT INTO %s (name, the_geom) VALUES ' % tableName
        statement += (
            "('%(name)s', ST_Force2D(ST_GeomFromKML('%(fragment)s')))" % track)
        results.append(statement)

    return results


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--table",
                        help="name of sql table for INSERT statment",
                        required=True)
    parser.add_argument("filename", help="filename of kml file to read")
    args = parser.parse_args()
    tracks = TracksFromKml(args.filename)
    statements = InsertsFromTracks(args.table, tracks)
    print '\n'.join(statements)


if __name__ == '__main__':
    main(sys.argv)
