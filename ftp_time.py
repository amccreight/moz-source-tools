#!/usr/bin/python

# FTP parser unit test date fixer.

# The unit tests seem to be written assuming the local system is in
# the same time zone as Paris, but for testing purposes it is easier
# to just use GMT. This script does the conversion.

import argparse
import datetime
from datetime import datetime
import os
import pytz

dateFormatString = "%m-%d-%Y  %H:%M:%S"

sourceTimeZone = pytz.timezone('Europe/Paris')


def fileAnalyzer(fname):
    print "Analyzing", fname

    f = open(fname, "r")
    newFile = open(fname + ".intermediate", "w")

    for l in f:
        if not l[0].isdigit():
            newFile.write(l)
            continue

        # R-dls.out includes dates like this, which the date parsing
        # library does not like.
        if l.startswith("00-00-0000  00:00:00"):
            newFile.write(l)
            continue

        dateTimeString = l[:20]
        dateTime = datetime.strptime(dateTimeString, dateFormatString)
        dateTime = sourceTimeZone.localize(dateTime).astimezone(pytz.utc)
        newString = datetime.strftime(dateTime, dateFormatString)

        newFile.write(newString + l[20:])

    f.close()
    newFile.close()
    os.rename(fname + ".intermediate", fname)


parser = argparse.ArgumentParser(description='Fix FTP unit test times.')
parser.add_argument('fileName', metavar='F',
                    help='Full path of directory to open files from')

args = parser.parse_args()

fileAnalyzer(args.fileName)
