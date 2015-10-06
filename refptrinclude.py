#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Analyze the need for includes of nsRefPtr.h vs nsAutoPtr.h

import re
import os
import argparse


typeUsePatt = re.compile('(nsAutoPtr|nsRefPtr|nsCOMPtr|nsAutoArrayPtr)\<')
arrayPatt = re.compile('Array')


def fileAnalyzer(args, fname):
    f = open(fname, "r")

    includes = set([])
    uses = set([])

    for l in f:
        if l.startswith('#include'):
            if 'mozilla/nsRefPtr.h' in l:
                includes.add('nsRefPtr')
            elif 'nsAutoPtr.h' in l:
                includes.add('nsAutoPtr')
            elif 'nsCOMPtr.h' in l:
                includes.add('nsCOMPtr')
            continue

        tuMatch = typeUsePatt.search(l)
        if not tuMatch:
            continue

        # Ignore lines that are definitely comments.
        if l.lstrip().startswith('//'):
            continue

        uses.add(re.sub(arrayPatt, '', tuMatch.group(1)))

    f.close()

    toRemove = includes - uses
    toAdd = uses - includes
    if toRemove or toAdd:
        print 'file:', fname,
        if toAdd:
            print 'add:', ', '.join(toAdd), '\t',
        if toRemove:
            print 'remove:', ', '.join(toRemove),
        print


parser = argparse.ArgumentParser(description='Analyze nsRefPtr includes.')
parser.add_argument('directory', metavar='D',
                    help='Full path of directory to open files from')

args = parser.parse_args()

for (base, _, files) in os.walk(args.directory):
    for fileName in files:
        if not (fileName.endswith('.h') or fileName.endswith('.cpp')):
            continue

        if not base.endswith("/"):
            base += "/"
        fullFileName = base + fileName

        fileAnalyzer(args, fullFileName)
