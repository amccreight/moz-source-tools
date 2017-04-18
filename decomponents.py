#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Modeline analyzer.

import re
import os
import argparse

# XXX probably also let and var.
ciPatt = re.compile("^\s*const\s+Ci\s*=\s*Components.interfaces\s*;$")


#const { utils: Cu, interfaces: Ci, classes: Cc, results: Cr } = Components;
fieldPatt = "\w+\s*:\s*\w+\s*"
bodyPatt = fieldPatt + "(?:,\s*" + fieldPatt + ")*"
destructurePatt = re.compile("^\s*(const|let|var)\s*\{\s*(" + bodyPatt + ")\}\s*=\s*Components\s*;$")


def extractFieldVals(s):
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
            if e1 == "interfaces" and e2 == "Ci":
                removedAny = True
                continue
            l.append((e1, e2))
        else:
            first = e

    if not removedAny:
        return None

    if not l:
        return ""

    # XXX In practice, we're going to remove them all, so don't worry
    # about a fancy pretty printer.  Though should throw in that case
    # once I'm trying to get this working for real.
    s = ""
    for e in l:
        s += e[0] + ": " + e[1] + ", "
    s = s.rstrip(", ")

    return s


def fileAnalyzer(args, fname):
    f = open(fname, "r")
    if args.fixFiles:
        newFile = open(fname + ".intermediate", "w")

    for l in f:
        if ciPatt.match(l):
            print("Skipping simple Ci match in " + fname)
            continue

        deMatch = destructurePatt.match(l)
        if deMatch:
            x = extractFieldVals(deMatch.group(2))
            if x == "":
                print("Removed all fields in " + fname)
                continue
            if x:
                print("Removing fields in " + fname)
                if args.fixFiles:
                    newFile.write(deMatch.group(1) + " { " + x + " } = Components;\n")
                    continue

        if args.fixFiles:
            newFile.write(l)

    f.close()

    if args.fixFiles:
        newFile.close()
        os.rename(fname + ".intermediate", fname)


parser = argparse.ArgumentParser(description='Remove definitions of Cc, Ci, Cr, Cu')
parser.add_argument('directory', metavar='D',
                    help='Full path of directory to open files from')

parser.add_argument('--fix', dest='fixFiles', action='store_true',
                    help='Fix any errors that are found')

args = parser.parse_args()

for (base, _, files) in os.walk(args.directory):
    for fileName in files:
        if not (fileName.endswith('.js') or fileName.endswith('.jsm')):
            continue

        # XXX Hacky way to not process files in the objdir.
        if "obj-dmd.noindex" in base:
            continue

        if not base.endswith("/"):
            base += "/"
        fullFileName = base + fileName

        fileAnalyzer(args, fullFileName)
