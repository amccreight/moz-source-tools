#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Replace text in files matching a pattern.

import re
import os
import argparse

# To save time, only look at file types that we think will contain C++.
fileNamePatt = re.compile("^.+\\.(?:cpp|h|cc|mm)$")

def fileAnalyzer(args, fname, encoding):
    f = open(fname, "r", encoding=encoding)
    anyFixes = False

    if args.fixFiles:
        newFile = open(fname + ".intermediate", "w")

    for l in f:
        l2 = l.replace("MOZ_DIAGNOSTIC_ASSERT(false, ", "MOZ_DIAGNOSTIC_CRASH(")
        if l2 == l:
            l2 = l.replace("MOZ_DIAGNOSTIC_ASSERT(false,", "MOZ_DIAGNOSTIC_CRASH(")
        if l2 != l:
            print("found something in file %s" % fname)
            anyFixes = True
            if args.fixFiles:
                newFile.write(l2)
                continue
            print(l[:-1])
            print(l2[:-1])
            continue
        if args.fixFiles:
            newFile.write(l)

    f.close()

    if args.fixFiles:
        newFile.close()
        if anyFixes:
            os.rename(fname + ".intermediate", fname)
        else:
            os.remove(fname + ".intermediate")


parser = argparse.ArgumentParser(description='Replace text in C++ files')
parser.add_argument('directory', metavar='D',
                    help='Full path of directory to open files from')

parser.add_argument('--fix', dest='fixFiles', action='store_true',
                    help='Fix any errors that are found')

args = parser.parse_args()


for (base, _, files) in os.walk(args.directory):
    for fileName in files:
        if not fileNamePatt.match(fileName):
            continue

        # XXX Hacky way to not process files in the objdir.
        if "mc/obj-" in base:
            continue

        if not base.endswith("/"):
            base += "/"
        fullFileName = base + fileName

        try:
            fileAnalyzer(args, fullFileName, "utf8")
        except UnicodeDecodeError:
            print("utf8 encoding failed for " + fullFileName)
            fileAnalyzer(args, fullFileName, "latin-1")
