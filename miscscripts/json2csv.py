#!/bin/python

"""json2csv

A quick script which takes a repeated block of json and writes it to a csv file.

It assumes the first entry in the list has the correct fields.

Surely there's lots of better tools out there than this, but it was quicker 
to write this than to find it.

Note: This code is completely unsafe as it runs 'eval' on a command line arg! 
It doesn't even bother to set locals or globals.

Usage:
  json2csv input.json output.csv "expr-to-get-values"
  
  The input will be in 'jsondict' in the eval expr.
  
Example:
  json2csv stats.json stats.csv "jsondict['jurisdictionStats'][0]['timeseries']"

  json2csv arcgisresult.json arcgisresult.csv \
    "[f['attributes'] for f in jsondict['features']]"

Matthew Blain, Dec 2020
"""


import csv
import json
import sys


def get_entries(jsondict, entry_expr):
    return eval(entry_expr)


def write_entries(fcsv, entries):
    writer = csv.DictWriter(fcsv, sorted(entries[0].keys()))
    writer.writeheader()
    writer.writerows(entries)


def json2csv(fjson, fcsv, entry_expr):
    jsondict = json.load(fjson)
    entries = get_entries(jsondict, entry_expr)
    write_entries(fcsv, entries)


def main(argv):
    with open(argv[1], "r") as fjson:
        with open(argv[2], "w") as fcsv:
            json2csv(fjson, fcsv, argv[3])


if __name__ == "__main__":
    main(sys.argv)
