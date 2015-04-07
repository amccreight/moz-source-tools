#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Modeline analyzer.

import re
import os
import argparse


commentyLinePatt = re.compile("^\s*\*")
wsPatt = re.compile("^([ ]+)")
tabPatt = re.compile("^(\t+)")


# from https://developer.mozilla.org/en-US/docs/Mozilla/Developer_guide/Coding_Style#Mode_Line
firstModeLine = "/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */\n"
secondModeLine = "/* vim: set ts=8 sts=2 et sw=2 tw=80: */\n"

firstModeLinePatt = re.compile("/\* -\*- Mode: C\+\+; tab-width: (\d+); indent-tabs-mode: nil; c-basic-offset: (\d+) -\*- \*/\n")

mplStart = "/* This Source Code Form is subject to the terms of the Mozilla Public\n"

def fileAnalyzer(fname):
    f = open(fname, "r")

    count0 = 0
    count2 = 0
    count4 = 0
    countOther = 0

    whichLine = 0

    for l in f:
        whichLine += 1

        # If we're at the start of a file, see if it has the proper modeline.
        if whichLine == 1 and l != firstModeLine:
            fmlp = firstModeLinePatt.match(l)
            if fmlp:
                print 'First line of', fname, 'does not quite match mode line:', fmlp.group(1), fmlp.group(2)
            else:
                print 'First line of', fname, 'does not match mode line:', l[:-1]
        if whichLine == 2 and l != secondModeLine:
            if l == mplStart:
                print 'Second line is MPL instead of VIM modeline'
            else:
                print 'Second line of', fname, 'does not match:', l[:-1]

        # Analyze indentation
        if commentyLinePatt.match(l):
            # Lines that start with * are probably comments, so ignore them.
            continue
        indent = 0
        wsm = wsPatt.match(l)
        if wsm:
            indent = len(wsm.group(1))
        if indent == 0:
            count0 += 1
            continue
        if indent % 2 == 0:
            count2 += 1
        if indent % 4 == 0:
            count4 += 1
        elif indent % 2 != 0:
            countOther += 1

    # XXX space it out for now
    print

    probablyIndentedBy = -1
    if (count2 + count4 + countOther) / 2 < 10:
        # This file is small, so just assume it is okay.
        return 2
    if count2 > (count2 + count4 + countOther) / 2:
        probablyIndentedBy = 2
    if count4 > (count2 + count4 + countOther) / 2:
        assert count2 <= (count2 + count4 + countOther) / 2
        probablyIndentedBy = 4
    if countOther > (count2 + count4 + countOther) / 2:
        print 'Weird file', fname
        print '\tcount0: ', count0
        print '\tcount2: ', count2
        print '\tcount4: ', count4
        print '\tcountOther: ', countOther
        assert False
    return probablyIndentedBy



parser = argparse.ArgumentParser(description='Analyze mode lines.')
parser.add_argument('directory', metavar='D',
                    help='Full path of directory to open files from')

args = parser.parse_args()

base = args.directory

for fileName in os.listdir(base):
    if not (fileName.endswith('.h') or fileName.endswith('.cpp')):
        continue
    fileName = base + fileName
    fileAnalyzer(fileName)
