#!/usr/bin/env python
"""CSV Column Splitter

Splits a CSV column into a few more columns.

A basic hard-coded ET(no L) tool.

Reads stdin, writes stdout.

Example usage:
 python columnsplitter.py  < 2016_general_early_voting_schedule_geom.csv > schedule_as_events.csv

"""

__author__ = 'Matthew Blain'

import argparse
import sys
import csv
import datetime
import re

def resplitfile(instream, outstream):
    """Read a CSV, split some columns, write some nonsense.

    This reads in a row which has a few columns:
     * LOCATION, ADDRESS, the_geom: Location of a polling place. (Human
       description, street address, encoded geometry).
     * Date (e.g. 11/3/2016): Hours for a particular date, in the form 11 a.m. - 6 p.m.
       or CLOSED

    It then outputs this as a bunch of events:
     * LOCATION, ADDRESS, the_geom: Location, as before.
     * event_time: Time of open or close.
     * duration: Duration of event, if open, in seconds. (Not sure of or usefulness?)
     * end_time: Time of close, if event is open time.
     * openclose: 1 for open, -1 for close. This lets us do cumulative sums so that the
       value will bounce between 0 (closed) and 1 (opened) for torque.
    """
    reader = csv.DictReader(instream)
    fieldnames = ['LOCATION','ADDRESS','the_geom','event_time', 'duration',
                  'end_time', 'openclose']

    results = []

    for row in reader:
      for k in sorted(row.keys()):
        if re.match('\d{1,2}\/\d{1,2}\/\d{4}', k):
          v = row[k]
          times = re.match('(\d{1,2}) a.m. - (\d{1,2}) p.m.', v)
          if times:
            open_time = datetime.datetime.strptime('%s %s' % (k, times.groups()[0]),
              '%m/%d/%Y %H')
            close_time = datetime.datetime.strptime('%s %s' % (k, times.groups()[1]),
              '%m/%d/%Y %H')
            # strptime doesn't handle the concept of am/pm well, so we'll just
            # add 12 hours?!
            close_time += datetime.timedelta(hours=12)
            open_row = {}
            # Copy the fixed fields.
            for k in ('LOCATION','ADDRESS','the_geom'):
              open_row[k] = row[k]
            close_row = dict(open_row)
            open_row['event_time'] = open_time.isoformat()
            open_row['duration'] = str((close_time-open_time).total_seconds())
            open_row['end_time'] = close_time.isoformat()
            open_row['openclose'] = '1'
            close_row['event_time'] = close_time.isoformat()
            close_row['openclose'] = '-1'

            results.append(open_row)
            results.append(close_row)

    writer = csv.DictWriter(outstream, fieldnames=fieldnames)
    writer.writeheader()
    for result in results:
      writer.writerow(result)


def main(argv):
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    resplitfile(sys.stdin, sys.stdout)


if __name__ == '__main__':
    main(sys.argv)
