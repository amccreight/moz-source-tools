#!/usr/bin/python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Modeline analyzer.

import re
import os
import argparse

# Skip lines that match this pattern.
linePatt = re.compile("^NS_IMPL_CYCLE_COLLECTION_(?:UN)?ROOT_NATIVE")

# Skip files that have these anywhere in their path.
wideDirIgnoreList = []

# Don't try to fix files in these directories.
dirIgnoreList = []

# Don't try to fix these files.
fileIgnoreList = []

def patternifyList(l):
    return re.compile("^.*(?:{core})$".format(core = "|".join([re.escape(s) for s in l])))


wideDirIgnoreList = re.compile("^.*(?:{core}).*$".format(core = "|".join([re.escape(s) for s in wideDirIgnoreList])))

dirIgnoreListPatt = patternifyList(dirIgnoreList)
fileIgnoreListPatt = patternifyList(fileIgnoreList)


def fileInIgnoreList(base, fileName):
    if wideDirIgnoreList.match(base):
        return True

    if dirIgnoreListPatt.match(base):
        return True

    if fileIgnoreListPatt.match(base + fileName):
        return True

    return False


def fileAnalyzer(args, fname):
    f = open(fname, "r")
    skipNext = False

    if args.fixFiles:
        tempFileName = fname + ".intermediate"
        anyFixed = False
        newFile = open(tempFileName, "w")

    for l in f:
        if skipNext:
            print("\tSkipped line " + l[:-1])
            skipNext = False
            continue

        lp = linePatt.match(l)
        if lp:
            print("Matched line " + l[:-1])
            anyFixed = True
            if l[-2] != ")":
                skipNext = True
            continue
        if args.fixFiles:
            newFile.write(l)

    f.close()

    if args.fixFiles:
        newFile.close()
        if anyFixed:
            os.rename(tempFileName, fname)
        else:
            os.remove(tempFileName)


parser = argparse.ArgumentParser(description='Analyze mode lines.')
parser.add_argument('directory', metavar='D',
                    help='Full path of directory to open files from')

parser.add_argument('--fix', dest='fixFiles', action='store_true',
                    help='Fix any errors that are found')

args = parser.parse_args()

ignorelist = []

for (base, _, files) in os.walk(args.directory):

    for fileName in files:
        if not fileName.endswith('.cpp'):
            continue

        if not base.endswith("/"):
            base += "/"
        fullFileName = base + fileName

#        if fileInIgnoreList(base, fileName):
#            ignorelist.append(fullFileName)
#            continue

        fileAnalyzer(args, fullFileName)

if ignorelist:
    print('Skipped files due to ignore list:')
    for f in ignorelist:
        print('   ' + f)
