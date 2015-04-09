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
fullWhitespacePatt = re.compile("^(\s+)")


# from https://developer.mozilla.org/en-US/docs/Mozilla/Developer_guide/Coding_Style#Mode_Line
firstModeLine = "/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */\n"
secondModeLine = "/* vim: set ts=8 sts=2 et sw=2 tw=80: */\n"

firstModeLinePatt = re.compile("^\s*/\* (?:-|a)\*-\s+Mode: (?:C|C\+\+|c\+\+|IDL);? (?:tab-width|c-basic-offset): \d+; indent-tabs-mode: nil; (?:tab-width|c-basic-offset): \d+;? -\*-\s*(.*)$")
# For some reason, many SVG mode lines start with a*- rather than -*-.

commentClosePatt = re.compile("^\s*\*/\n")

mplStart = "/* This Source Code Form is subject to the terms of the Mozilla Public\n"
mplOtherStart = " * This Source Code Form is subject to the terms of the Mozilla Public\n"
mplSecond = " * License, v. 2.0. If a copy of the MPL was not distributed with this\n"
mplSpacerPatt = re.compile("^\s+\*\s*$")


# Skip files that have these anywhere in their path.
wideDirBlackList = [
    'xpcom/reflect', # This dir seems all 4-space indented.
    'dom/media/', # There's a lot of this, and lots is imported.
    'dom/plugins/',
    'dom/xslt/',
    'dom/xul/',
  ]

# Don't try to fix files in these directories, which have a lot of
# files with 4-space indent.
dirBlackList = [
    'xpcom/tests/',
    'xpcom/tests/static-checker/',
    'xpcom/tests/windows/',
    'xpcom/typelib/xpt/',
    'xpcom/typelib/xpt/tests/',
    'xpcom/tests/',
    'dom/camera/',
    'dom/canvas/',
    'dom/system/qt/',
    # Lots of Apache-style licenses in this directory that aren't dealt with by the script.
    'dom/system/gonk/',
    'dom/system/gonk/android_audio/',
  ]

# Don't try to fix these files.
fileBlackList = [
    # Not regular source files.
    'xpcom/base/ErrorList.h',
    'dom/webidl/CSS2PropertiesProps.h',
    # Imported.
    'xpcom/base/pure.h',
    'xpcom/build/mach_override.h',
    'xpcom/glue/nsQuickSort.cpp',
    'bluedroid/b2g_bdroid_buildcfg.h',
    # Some other license besides MPL.
    'xpcom/glue/tests/gtest/TestFileUtils.cpp',
    'bluedroid/BluetoothServiceBluedroid.cpp',
    'bluez/BluetoothDBusService.cpp',
    'bluez/BluetoothUnixSocketConnector.cpp',
    'dom/canvas/MurmurHash3.cpp',
    'dom/canvas/MurmurHash3.h',
    # Odd tiny header.
    'xpcom/io/crc32c.h',
    # Partially or fully 4-space indented.
    'xpcom/tests/gtest/TestSynchronization.cpp',
    'xpcom/tests/gtest/TestTimeStamp.cpp',
    'xpcom/tests/gtest/TestXPIDLString.cpp', # Also missing license header.
    'xpcom/base/nsAgg.h',
    'xpcom/components/ModuleUtils.h',
    'xpcom/windbgdlg/windbgdlg.cpp',
    'dom/base/NodeIterator.cpp',
    'dom/base/NodeIterator.h',
    'dom/base/nsContentPolicy.cpp',
    'dom/base/nsContentPolicy.h',
    'dom/base/nsContentPolicyUtils.h',
    'dom/base/nsCopySupport.h',
    'dom/base/nsSyncLoadService.cpp',
    'dom/base/nsTraversal.cpp',
    'dom/base/nsTreeSanitizer.h',
    'dom/base/nsViewportInfo.h',
    'dom/base/TreeWalker.cpp',
    'dom/base/TreeWalker.h',
    'dom/ipc/ContentChild.cpp',
    'dom/ipc/ContentChild.h',
    'dom/ipc/ContentParent.cpp',
    'dom/ipc/ContentParent.h',
    'dom/ipc/CrashReporterParent.cpp',
    'dom/ipc/TabParent.h',
    'dom/jsurl/nsJSProtocolHandler.cpp',
    'dom/jsurl/nsJSProtocolHandler.h',
    'dom/xml/nsXMLPrettyPrinter.cpp',
    'dom/xml/nsXMLPrettyPrinter.h',
  ]

# Don't complain about apparently invalid indentation for these files.
# Mostly these are files that have a bunch of declarations or methods
# with short bodies.
indentWhiteList = [
    'xpcom/io/nsStreamUtils.h',
    'xpcom/string/nsReadableUtils.h',
    'xpcom/build/nsXULAppAPI.h',
    'xpcom/build/ServiceList.h',
    'xpcom/tests/gtest/TestThreads.cpp',
    'xpcom/tests/gtest/TestUTF.cpp',
    'dom/base/FeedWriterEnabled.h',
    'dom/base/NodeInfoInlines.h',
    'dom/base/nsContentCID.h',
    'dom/base/nsIDocumentObserver.h',
    'dom/base/nsIMutationObserver.h',
    'dom/base/nsObjectLoadingContent.h',
    'dom/base/SubtleCrypto.cpp',
    'bluedroid/BluetoothDaemonAvrcpInterface.h',
    'bluedroid/BluetoothDaemonHandsfreeInterface.h',
    'dom/cellbroadcast/CellBroadcast.cpp',
    'dom/cellbroadcast/ipc/CellBroadcastParent.cpp',
    'dom/events/DeviceMotionEvent.cpp',
    'dom/events/DragEvent.cpp',
    'dom/events/DragEvent.h',
    'dom/events/MouseScrollEvent.cpp',
    'dom/events/SimpleGestureEvent.cpp',
    'dom/geolocation/nsGeoPositionIPCSerialiser.h',
    'dom/html/HTMLFrameElement.cpp',
    'dom/indexedDB/IDBIndex.cpp',
    'dom/ipc/AppProcessChecker.h',
    'dom/ipc/ContentBridgeChild.cpp',
    'dom/ipc/ContentBridgeChild.h',
    'dom/ipc/ContentBridgeParent.cpp',
    'dom/ipc/TabChild.h',
    'dom/mobileconnection/ipc/MobileConnectionIPCSerializer.h',
    'dom/mobilemessage/MmsMessage.h',
    'dom/mobilemessage/MobileMessageService.cpp',
    'dom/mobilemessage/SmsMessage.h',
    'dom/network/NetUtils.h',
    'dom/quota/StorageMatcher.h',
    'dom/security/nsCSPContext.h',
    'dom/security/nsCSPParser.h',
    'dom/security/nsCSPUtils.h',
    'dom/svg/SVGAnimateTransformElement.cpp',
    'dom/svg/SVGSymbolElement.cpp',
    'dom/telephony/TelephonyCallInfo.cpp',
    'dom/telephony/ipc/TelephonyIPCSerializer.h',
    'dom/tv/FakeTVService.h',
  ]


def patternifyList(l):
    return re.compile("^.*(?:{core})$".format(core = "|".join([re.escape(s) for s in l])))


wideDirBlackList = re.compile("^.*(?:{core}).*$".format(core = "|".join([re.escape(s) for s in wideDirBlackList])))

dirBlackListPatt = patternifyList(dirBlackList)
fileBlackListPatt = patternifyList(fileBlackList)
indentWhiteListPatt = patternifyList(indentWhiteList)


def fileInBlackList(base, fileName):
    if wideDirBlackList.match(base):
        return True

    if dirBlackListPatt.match(base):
        return True

    if fileBlackListPatt.match(base + fileName):
        return True

    return False

def fileInIndentWhiteList(fileName):
    if indentWhiteListPatt.match(fileName):
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
    tabCount = 0

    whichLine = 0

    anyErrors = False

    for l in f:
        whichLine += 1

        if args.tabs:
            fwp = fullWhitespacePatt.match(l)
            if fwp and fwp.group(1).count("\t") != 0:
                tabCount += 1

        # If we're at the start of a file, see if it has the proper modeline.
        if whichLine == 1 and l != firstModeLine:
            if l == "\n":
                # Skip leading blank lines.
                whichLine -= 1
                continue

            if args.fixFiles:
                newFile.write(firstModeLine)

            anyErrors = True
            fmlp = firstModeLinePatt.match(l)
            if fmlp:
                print 'First line of', fname, 'had incorrect C++ mode line'

                if fmlp.group(1) != "*/" and fmlp.group(1) != "":
                    print '\n\nERROR!!!!'
                    print 'Weird ending for first mode line:', fmlp.group(1),
                    exit(-1)
            elif l == '/* -*- Mode: c++; c-basic-offset: 4; tab-width: 20; indent-tabs-mode: nil; -*-\n':
                print 'First line of', fname, 'had dom/system/android/ style modeline'
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
            if l == "\n":
                # Skip blank lines after the Emacs mode line.
                whichLine -= 1
                continue

            if args.fixFiles:
                newFile.write(secondModeLine)

            anyErrors = True
            if l == mplStart or l == mplOtherStart:
                print 'Second line is MPL instead of VIM modeline'
                if args.fixFiles:
                    newFile.write(mplStart)
                whichLine += 1
            elif mplSpacerPatt.match(l):
                print 'Replacing MPL spacer with vim mode line.'
            elif vimishLine(l):
                print 'Second line is weird vim mode line:', l[:-1]
            else:
                print '\n\nERROR!!!!'
                print 'Second line of', fname, 'does not match:', l[:-1]
                exit(-1)

        elif whichLine == 3 and l != mplStart:
            if l == '\n' or commentClosePatt.match(l) or mplSpacerPatt.match(l):
                # Skip blank lines after the mode lines.
                print 'Skipping a useless looking third line'
                whichLine -= 1
                continue

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


        # Analyze indentation.
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

    if tabCount != 0:
        print 'TABS in file', fname, 'on', tabCount, 'lines.'

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
                print '\n\nERROR!!!!'
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

parser.add_argument('--tabs', dest='tabs', action='store_true',
                    help='Analyze leading tabs')

args = parser.parse_args()

for (base, _, files) in os.walk(args.directory):
    for fileName in files:
        if not (fileName.endswith('.h') or fileName.endswith('.cpp')):
            continue

        if not base.endswith("/"):
            base += "/"
        fullFileName = base + fileName

        if fileInBlackList(base, fileName):
            print 'Skipping file', fullFileName, 'due to blacklist'
            print
            continue

        fileAnalyzer(args, fullFileName)
