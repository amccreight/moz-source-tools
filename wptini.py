#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# WPT lsan-allowed ini file fixer.

import re
import os
import argparse


lsanAllowedPatt = re.compile("^lsan-allowed: \[(.*)\]")


ignorelistedDirectories = [
    # The base directory has some generic JS stuff.
    "",

    # Permaleaks.
    "html/semantics/forms/form-submission-0/", # bug 1517577
    "encrypted-media/", # bug 1517595
    "fetch/api/request/", # bug 1517600
    "FileAPI/file/", # bug 1518230
    "FileAPI/FileReader/", # bug 1517071
    "webauthn/", # bug 1517611
    "WebCryptoAPI/generateKey/", # bug 1517574
    "websockets/", # bug 1517601

    # Intermittent leaks.
    "fetch/api/basic/", # bug 1518298
    "fetch/api/abort/", # Leak of a single string.
    "infrastructure/server/", # Websocket stuff.
]


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

        allowlists = m.group(1).split(', ')

        if allowlists[0] == '':
            # Don't bother printing out empty allow lists.
            continue

        if 'nsHostResolver::ResolveHost' in allowlists:
            # This leak was fixed by bug 1467914.
            continue

        if True:
            # Try out removing allow lists from all non ignore listed files.
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

ignorelist = []

iniFileName = '__dir__.ini'
wptDirectory = 'testing/web-platform/meta'

directory = args.directory
if not directory.endswith("/"):
    directory += "/"
directory = args.directory + wptDirectory

ignorelistedDirPatt = re.compile('^{base}{wpt}(?:{dirs})$'.format(base = re.escape(args.directory),
                                                                  wpt = re.escape(wptDirectory),
                                                                  dirs = "|".join(["/" + re.escape(s) for s in ignorelistedDirectories])))


for (base, _, files) in os.walk(directory):
    if not iniFileName in files:
        continue

    if not base.endswith("/"):
        base += "/"

    if ignorelistedDirPatt.match(base):
        print 'Skipping ignore listed file in', base
        continue

    fullFileName = base + iniFileName
    fileAnalyzer(args, fullFileName)
