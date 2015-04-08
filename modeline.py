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

firstModeLinePatt = re.compile("^/\* -\*-\s+Mode: C\+*; tab-width: (\d+); indent-tabs-mode: nil; c-basic-offset: (\d+);? -\*-(.*)$")

mplStart = "/* This Source Code Form is subject to the terms of the Mozilla Public\n"
mplOtherStart = " * This Source Code Form is subject to the terms of the Mozilla Public\n"
mplSecond = " * License, v. 2.0. If a copy of the MPL was not distributed with this\n"
mplSpacer = " *\n"


# Don't try to fix files in these directories, which have a lot of
# files with 4-space indent.
dirBlackList = [
    'xpcom/tests',
    'xpcom/tests/static-checker',
    'xpcom/tests/windows',
    'xpcom/typelib/xpt',
    'xpcom/typelib/xpt/tests',
  ]

dirBlackListPatt = re.compile("%s$".format("|".join(dirBlackList)))

# Don't try to fix these files.
fileBlackList = [
    # Not a regular source file.
    'xpcom/base/ErrorList.h',
    # Imported.
    'xpcom/base/pure.h',
    'xpcom/build/mach_override.h',
    'xpcom/glue/nsQuickSort.cpp',
    # Public domain instead of MPL.
    'xpcom/glue/tests/gtest/TestFileUtils.cpp',
    # Odd tiny header.
    'xpcom/io/crc32c.h',
    # Partially or fully 4-space indented.
    'xpcom/tests/gtest/TestSynchronization.cpp',
    'xpcom/tests/gtest/TestTimeStamp.cpp',
    'xpcom/base/nsAgg.h',
    'xpcom/components/ModuleUtils.h',
    'xpcom/tests/gtest/TestXPIDLString.cpp', # Also missing license header.
  ]

# Don't complain about apparently invalid indentation for these files.
indentWhiteList = [
    # Mostly function decls, so there are few normal lines.
    'xpcom/io/nsStreamUtils.h',
    'xpcom/string/nsReadableUtils.h',
    'xpcom/build/nsXULAppAPI.h',
    # Formatting is a little weird, but looks 2-space indented to me.
    'xpcom/tests/gtest/TestThreads.cpp',
    'xpcom/tests/gtest/TestUTF.cpp',
  ]


def fileInBlackList(base, fileName):
    # This directory seems to be all 4-space indented.
    if 'xpcom/reflect' in base:
        return True

    dblm = dirBlackListPatt.match(base)
    if dblm:
        return True

    fullFileName = base + '/' + fileName
    for f in fileBlackList:
        if fullFileName.endswith(f):
            return True
    return False

def fileInIndentWhiteList(fileName):
    for f in indentWhiteList:
        if fileName.endswith(f):
            return True
    return False


def vimishLine(l):
    return l.startswith('/* vim:') or l.startswith('// vim:') or l.startswith(' * vim:')

def fileAnalyzer(args, fname):
    f = open(fname, "r")

    if args.fixFiles:
        newFile = open(fname + ".intermediate", "w")

    count0 = 0
    count2 = 0
    count4 = 0
    countOther = 0

    whichLine = 0

    anyErrors = False

    for l in f:
        whichLine += 1

        # If we're at the start of a file, see if it has the proper modeline.
        if whichLine == 1 and l != firstModeLine:
            if args.fixFiles:
                newFile.write(firstModeLine)

            anyErrors = True
            fmlp = firstModeLinePatt.match(l)
            if fmlp:
                print 'First line of', fname, 'had tab-width', fmlp.group(1), 'and c-basic-offset', fmlp.group(2)

                if fmlp.group(3) != " */" and fmlp.group(3) != "":
                    print 'Weird ending for first mode line:', fmlp.group(3)
                    exit(-1)
            elif l == mplStart:
                print 'First line of', fname, 'is MPL instead of Emacs modeline'
                if args.fixFiles:
                    newFile.write(secondModeLine)
                    newFile.write(mplStart)
                whichLine += 2
            elif vimishLine(l):
                if l == secondModeLine:
                    print 'First line of', fname, 'is vim modeline'
                else:
                    print 'First line of', fname, 'is nonstandard vim modeline'

                if args.fixFiles:
                    newFile.write(secondModeLine)
                whichLine += 1
            else:
                print '\n\nERROR!!!!'
                print 'First line of', fname, 'does not match mode line:', l[:-1]
                exit(-1)

        elif whichLine == 2 and l != secondModeLine:
            if args.fixFiles:
                newFile.write(secondModeLine)

            anyErrors = True
            if l == mplStart or l == mplOtherStart:
                print 'Second line is MPL instead of VIM modeline'
                if args.fixFiles:
                    newFile.write(mplStart)
                whichLine += 1
            elif l == mplSpacer:
                print 'Replacing MPL spacer with vim mode line.'
            elif vimishLine(l):
                print 'Second line is weird vim mode line:', l[:-1]
            else:
                print '\n\nERROR!!!!'
                print 'Second line of', fname, 'does not match:', l[:-1]
                exit(-1)

        elif whichLine == 3 and l != mplStart:
            if l == mplOtherStart:
                if args.fixFiles:
                    newFile.write(mplStart)
                anyErrors = True
                print 'Third line is not MPL proper start'
            else:
                print '\n\nERROR!!!!'
                print 'Third line of', fname, 'is weird:', l[:-1]
                exit(-1)

        elif args.fixFiles:
            newFile.write(l)


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

    f.close()

    if args.fixFiles:
        newFile.close()
        os.rename(fname + ".intermediate", fname)

    if anyErrors:
        print

    # Check that this file is probably indented by 2.
    probablyIndentedBy = -1
    if count2 + count4 + countOther < 30:
        # This file doesn't have many indented lines, so just assume it is okay.
        probablyIndentedBy = 2
    else:
        if count2 > (count2 + count4 + countOther) * 0.6:
            probablyIndentedBy = 2
        elif count4 > (count4 + countOther) * 0.6:
            probablyIndentedBy = 4
        elif countOther > (count2 + count4 + countOther) / 2:
            if fileInIndentWhiteList(fname):
                probablyIndentedBy = 2
            else:
                print 'File with lots of oddly indented lines', fname
                print '\tcount0: ', count0
                print '\tcount2: ', count2
                print '\tcount4: ', count4
                print '\tcountOther: ', countOther
                exit(-1)

    if probablyIndentedBy != 2 and not fileInIndentWhiteList(fname):
        print 'Weird file', fname
        print '\tcount0: ', count0
        print '\tcount2: ', count2
        print '\tcount4: ', count4
        print '\tcountOther: ', countOther

        print '\n\nERROR!!!!'
        print 'File', fname, 'was probably indented by', probablyIndentedBy, 'instead of by 2'
        exit(-1)


parser = argparse.ArgumentParser(description='Analyze mode lines.')
parser.add_argument('directory', metavar='D',
                    help='Full path of directory to open files from')

parser.add_argument('--fix', dest='fixFiles', action='store_true',
                    help='Fix any errors that are found')

args = parser.parse_args()

for (base, _, files) in os.walk(args.directory):
    for fileName in files:
        if not (fileName.endswith('.h') or fileName.endswith('.cpp')):
            continue

        fullFileName = base + '/' + fileName

        if fileInBlackList(base, fileName):
            print 'Skipping file', fullFileName, 'due to blacklist'
            print
            continue

        fileAnalyzer(args, fullFileName)
