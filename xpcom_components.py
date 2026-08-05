#!/usr/bin/python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Very simple XPCOM components manifest analyzer.
#
# Run this script from the top of the Firefox source directory. Pass in the
# name of a file that contains one XPCOM manifest per file.
# If you are only interested in singleton components, you can generate
# this file with the command rg -l \'singleton\' > conf.txt
# This script will filter out any file that isn't named components.conf,
# as all of the XPCOM component configuration files seem to be named that.
# Or you could get all of the conf files with something like
#   find . -type f -name "components.conf" > conf.txt

import argparse
import ast
import copy
import re
from pathlib import Path

classesRe = re.compile('Classes')
emptyClassesRe = re.compile(r'^\s*Classes = \[\]\s*$')
classesStartRe = re.compile(r'^\s*Classes [+]?= \[\s*$')
classesEndRe = re.compile(r'^\s*\]\s*$')

linkServiceStartRe = re.compile(r'^\s*link_service = {\s*$')
linkServiceEndRe = re.compile(r'^\s*}\s*$')
linkServiceUseRe = re.compile(r'\*\*link_service')

selectorRe = re.compile(r'(ProcessSelector|BackgroundTasksSelector).[A-Z_]+')

aboutProtocolRe1 = re.compile(r"'@mozilla.org/network/protocol/about;1\?what=%s' % path")
aboutProtocolRe2 = re.compile(r'for path in about_pages')
nameContentTypesRe = re.compile(r"'name': content_types,")
crashReporterRe = re.compile(r'\] \+ crash_reporter,')

def parseFile(fileName) :
    f = open(fileName, "r")

    state = 'NONE'
    currValueStrings = None
    classesData = []
    linkServiceValues = []

    for l in f:
        if classesRe.search(l):
            # A file shouldn't have Classes in the middle of a Classes, hopefully.
            assert state == 'NONE'

            # Ignore an empty Classes.
            if emptyClassesRe.fullmatch(l):
                continue

            isClassesStart = classesStartRe.fullmatch(l)
            assert isClassesStart
            state = 'Classes'
            currValueStrings = ['[\n']
            continue

        if state == 'NONE':
            if not linkServiceStartRe.fullmatch(l):
                continue
            assert fileName == 'netwerk/build/components.conf'
            state = 'link_service'
            currValueStrings = ['{\n']
            continue

        assert state == 'link_service' or state == 'Classes'

        if state == 'link_service' and linkServiceEndRe.fullmatch(l):
            currValueStrings.append(l)
            fullString = ''.join(currValueStrings)
            data = ast.literal_eval(fullString)
            linkServiceValues.append(data)

            state = 'NONE'
            classesString = None
            continue

        if state == 'Classes' and classesEndRe.fullmatch(l):
            currValueStrings.append(l)
            needLinkServiceHack = False
            for s in currValueStrings:
                if linkServiceUseRe.search(s):
                    needLinkServiceHack = True
                    break

            if needLinkServiceHack:
                # Remove the splicing so literal_eval can parse it.
                assert fileName == 'netwerk/build/components.conf'
                assert currValueStrings[1] == '        dict({\n'
                assert currValueStrings[-2] == '        }, **link_service)\n'
                currValueStrings[1] = '        {\n'
                currValueStrings[-2] = '        }'

            fullString = ''.join(currValueStrings)
            data = ast.literal_eval(fullString)

            if needLinkServiceHack:
                assert len(linkServiceValues) > 0
                assert isinstance(data, list)
                assert len(data) == 1
                assert isinstance(data[0], dict)
                for linkService in linkServiceValues:
                    dataClone = copy.deepcopy(data)
                    dataClone[0].update(linkService)
                    classesData.append(dataClone)
                linkServiceValues = []
            else:
                classesData.append(data)

            state = 'NONE'
            classesString = None
            continue

        # Various one-off fixes.
        if aboutProtocolRe1.search(l):
            # The about: pages protocols run code, but they
            # are also not singletons, so ignore them.
            assert fileName == 'docshell/build/components.conf'
            l = "'@mozilla.org/network/protocol/about;1?what=???'\n"
        if aboutProtocolRe2.search(l):
            # As above, but just skip the line.
            assert fileName == 'docshell/build/components.conf'
            l = '\n'
        if nameContentTypesRe.search(l):
            assert fileName == 'layout/build/components.conf'
            l = '\n'
        if crashReporterRe.search(l):
            assert fileName == 'toolkit/xre/components.conf'
            l = "'@mozilla.org/toolkit/crash-reporter;1'],\n"

        # Replace constants with strings so we can use literal_eval.
        l = re.sub(selectorRe, lambda m: f'"{m.group()}"', l)

        currValueStrings.append(l)

    assert len(linkServiceValues) == 0
    return classesData

# Return the contract_id and cid of singleton components defined in the file.
def analyzeFile(fileName):
    classesData = parseFile(fileName)

    singletonData = set([])
    for classes in classesData:
        for c in classes:
            if not c.get("singleton", False):
                continue
            for id in c.get('contract_ids'):
                singletonData.add((id, c.get('cid')))

    return singletonData


def printData(data):
    components = list(data)
    components.sort()
    for c in components:
        print(f'{c[0]} {c[1]}')


def analyzeFiles(fileNames):
    data = set([])

    for f in fileNames:
        data |= analyzeFile(f)
    printData(data)


def parseFileOfFiles(fileFileName):
    f = open(fileFileName, "r")

    filteredFileNames = []

    for fileName in f:
        # Remove the trailing new line.
        assert fileName[-1] == '\n'
        fileName = fileName[:-1]
        if Path(fileName).name != "components.conf":
            continue
        filteredFileNames.append(fileName)

    return filteredFileNames


parser = argparse.ArgumentParser(description='XPCOM singleton components analyzer.')
parser.add_argument('file', metavar='F',
                    help='File containing one possible singleton conf file per line.')
args = parser.parse_args()

analyzeFiles(parseFileOfFiles(args.file))
