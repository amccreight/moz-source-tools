#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Components remover.

import re
import os
import argparse

# let Cu = Components.utils;
ciPatt = re.compile("^\s*(const|let|var)\s+(Cc|Ci|Cr|Cu)\s*=\s*Components.(classes|interfaces|results|utils)\s*;\s*$")

# const { utils: Cu, interfaces: Ci, classes: Cc, results: Cr } = Components;
fieldPatt = "\w+\s*:\s*\w+\s*"
bodyPatt = fieldPatt + "(?:,\s*" + fieldPatt + ")*"
destructurePatt = re.compile("^(\s*(?:const|let|var))\s*(\{\s*)(" + bodyPatt + ")\}\s*=\s*Components\s*;\s*$")

whiteSpacePatt = re.compile("^\s*$")

matchDestructure = True

def extractFieldVals(prefix, bracketPrefix, s):
    removedAny = False
    first = None
    l = []

    for e in s.split():
        e = e.strip(":,")
        if e == "":
            continue
        if first:
            e1 = first
            e2 = e
            first = None
            if ((e1 == "interfaces" and e2 == "Ci") or
                (e1 == "utils" and e2 == "Cu") or
                (e1 == "classes" and e2 == "Cc") or
                (e1 == "results" and e2 == "Cr")):
                removedAny = True
                continue
            l.append((e1, e2))
        else:
            first = e

    if not removedAny:
        return None

    if not l:
        return ""

    if len(l) == 1:
        # If there's only one variable being defined, don't bother
        # with the fancy pattern matching syntax.
        return prefix + " " + l[0][1] + " = Components." + l[0][0]

    # XXX This doesn't seem to be needed anywhere in Firefox,
    # so this code may have bitrotted.
    s2 = ""
    for e in l:
        s2 += e[0] + ": " + e[1] + ", "
    s2 = s2.rstrip(", ")

    # In practice, these patterns have zero or one spaces at the end.
    # Make sure the trailing padding matches.
    if s[-1] == " ":
        assert s[-2] != " "
        s2 += " "

    return prefix + " " + bracketPrefix + s2 + "} = Components"


# Hacky work around for a few cases where a "block" starts with a let
# followed by a blank line, and we want to get rid of the blank
# line:
#   // at the start of the line for comments
#   */ at the end of the line for comments
#   { at the end of the line for blocks in JS
#   """ and ''' at the end of the line for Python with embedded JS.
blockStartPatt = re.compile("(?:^//)|(?:^.*(?:\*/|\{|\"\"\"|''')\n$)")

def fileAnalyzer(args, fname):
    f = open(fname, "r")
    anyFixes = False
    prevNotRemovedLineBlank = True
    removedLastLine = False

    if args.fixFiles:
        newFile = open(fname + ".intermediate", "w")

    for l in f:
        if ciPatt.match(l):
            print("Skipping simple Ci match in " + fname)
            anyFixes = True
            removedLastLine = True
            continue

        if matchDestructure:
            deMatch = destructurePatt.match(l)
            if deMatch:
                x = extractFieldVals(deMatch.group(1), deMatch.group(2), deMatch.group(3))
                if x == "":
                    print("Removed all fields in " + fname)
                    anyFixes = True
                    removedLastLine = True
                    continue
                if x:
                    print("Removing fields in " + fname)
                    anyFixes = True
                    prevNotRemovedLineBlank = False
                    removedLastLine = False
                    if args.fixFiles:
                        newFile.write(x + ";\n")
                        continue

        currLineBlank = bool(whiteSpacePatt.match(l))
        if removedLastLine and prevNotRemovedLineBlank and currLineBlank:
            continue

        prevNotRemovedLineBlank = currLineBlank or blockStartPatt.match(l)
        removedLastLine = False

        if args.fixFiles:
            newFile.write(l)

    f.close()

    if args.fixFiles:
        newFile.close()
        if anyFixes:
            os.rename(fname + ".intermediate", fname)
        else:
            os.remove(fname + ".intermediate")


parser = argparse.ArgumentParser(description='Remove definitions of Cc, Ci, Cr, Cu')
parser.add_argument('directory', metavar='D',
                    help='Full path of directory to open files from')

parser.add_argument('--fix', dest='fixFiles', action='store_true',
                    help='Fix any errors that are found')

args = parser.parse_args()

# To save time, only look at file types that we think will contain JS.
fileNamePatt = re.compile("^.+\.(?:js|jsm|html|py|sjs|xhtml|xul)$")

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

        fileAnalyzer(args, fullFileName)
