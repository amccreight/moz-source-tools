#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Modeline analyzer.

import re
import os
import argparse


lsanAllowedPatt = re.compile("^lsan-allowed: \[(.*)\]")

def fileAnalyzer(args, fname):
    f = open(fname, "r")

    if args.fixFiles:
        newFile = open(fname + ".intermediate", "w")

    for l in f:
        m = lsanAllowedPatt.match(l)
        if not m:
            if args.fixFiles:
                newFile.write(l)
            continue

        whitelists = m.group(1).split(',')

        if whitelists[0] == '':
            # Don't bother printing out empty white lists.
            continue

        if args.fixFiles:
            newFile.write(l)

    f.close()

    if args.fixFiles:
        newFile.close()
        os.rename(fname + ".intermediate", fname)


parser = argparse.ArgumentParser(description='Edit WPT ini files.')
parser.add_argument('directory', metavar='D',
                    help='Base path of source directory to find WPT ini files')

parser.add_argument('--fix', dest='fixFiles', action='store_true',
                    help='Fix any errors that are found')

args = parser.parse_args()

blacklist = []

directory = args.directory + 'testing/web-platform/meta/'

for (base, _, files) in os.walk(args.directory):
    for fileName in files:

        if fileName != '__dir__.ini':
            continue

        if not base.endswith("/"):
            base += "/"
        fullFileName = base + fileName
        fileAnalyzer(args, fullFileName)
