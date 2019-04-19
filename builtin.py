#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# The idea of this script is to find interfaces that are not
# implemented in JS, but not marked builtinclass.

import re
import os
import argparse


okayInterfacePatt = re.compile("^nsI|xpcI|mozI|nsPI|imgI|rrI|amI|txI|IPeer")

weirdInterfacesToIgnore = [
    "IJSDebugger",
    "inIDeepTreeWalker",
    "IUrlClassifierUITelemetry",
]
weirdInterfacesToIgnorePatt = re.compile("^" + "|".join(weirdInterfacesToIgnore) + "$")

def assertInterfaceOkay(fname, interface):
    if okayInterfacePatt.match(interface):
        return
    if weirdInterfacesToIgnorePatt.match(interface):
        return
    raise Exception("Bad interface " + interface + " in file " + fname)


# Look for calls to ChromeUtils.generateQI and add any interfaces found to the
# set |jsImplementedInterfaces|.
def generateQIFinder(args, fname, jsImplementedInterfaces):
    f = open(fname, "r")
    qiArgString = None

    for l in f:
        l = l.strip()

        # Skip lines that are comments or are probably part of comments.
        if l.startswith("//") or l.startswith("*"):
            continue

        if not qiArgString:
            if not "ChromeUtils.generateQI" in l:
                continue
            qiArgString = ""
            l = l.split("ChromeUtils.generateQI")[1]

        l = l.split(")")
        qiArgString += l[0].strip()
        if len(l) == 1:
            continue

        rawInterfaces = qiArgString.strip("([],").split(",")
        for r in rawInterfaces:
            interface = r.strip('" ')
            if interface == "":
                continue

            # Ignore some weird cases in test files.
            if interface.endswith("interfaces"):
                if (fname.endswith("js/xpconnect/tests/unit/test_generateQI.js") or
                    fname.endswith("netwerk/test/browser/browser_nsIFormPOSTActionChannel.js") or
                    fname.endswith("testing/modules/AppInfo.jsm") or
                    fname.endswith("browser/components/places/content/browserPlacesViews.js")):
                    continue
            if interface == "observerInterface":
                if fname.endswith("browser/components/newtab/lib/PlacesFeed.jsm"):
                    continue
            if interface == "ifaces":
                if (fname.endswith("toolkit/content/customElements.js") or
                    fname.endswith("toolkit/mozapps/update/tests/data/xpcshellUtilsAUS.js")):
                    continue
            if interface == "iface":
                if fname.endswith("toolkit/components/places/tests/PlacesTestUtils.jsm"):
                    continue

            if interface.startswith("Ci."):
                interface = interface[3:]
            elif interface.startswith('Ci["'):
                interface = interface[4:]
            elif interface.startswith("parentCi."):
                interface = interface[9:]
            assertInterfaceOkay(fname, interface)
            jsImplementedInterfaces.add(interface)

        qiArgString = None

    f.close()


# Look at XPIDL files for interfaces that are not marked builtinclass.
def idlFileAnalyzer(args, fname, jsImplementedInterfaces, nonBuiltinInterfaces):
    f = open(fname, "r")
    prevLine = None

    for l in f:
        l = l.strip()
        if l.startswith("//"):
            continue
        if not l.startswith("interface "):
            prevLine = l
            continue
        if l.endswith(";"):
            # Just a forward declaration. Ignore it.
            prevLine = None
            continue
        interface = l.split()[1].strip(":")
        assertInterfaceOkay(fname, interface)

        attributes = prevLine.strip().strip("[]").split(", ")
        builtinClass = False
        anyUUID = False
        for a in attributes:
            if a == 'builtinclass':
                builtinClass = True
                continue
            if a.startswith('uuid'):
                assert not anyUUID
                anyUUID = True
                continue
        if not anyUUID:
            print fname, prevLine
        assert anyUUID
        if not builtinClass:
            nonBuiltinInterfaces.add(interface)


    f.close()



# Finally, print out a list of interfaces in the second group but not the first. Ideally, auto fix.


parser = argparse.ArgumentParser(description='Find XPIDL interfaces that could be marked builtinclass')
parser.add_argument('directory', metavar='D',
                    help='Full path of directory to open files from')

parser.add_argument('--fix', dest='fixFiles', action='store_true',
                    help='Fix any errors that are found')

args = parser.parse_args()

jsImplementedInterfaces = set([])
nonBuiltinInterfaces = set([])

for (base, _, files) in os.walk(args.directory):
    for fileName in files:
        #if not (fileName.endswith('.js') or fileName.endswith('.jsm')):
        #    continue

        if fileName.endswith('.cpp') or fileName.endswith('.h') or fileName.endswith('~'):
            continue

        # XXX Hacky way to not process files in the objdir.
        if "obj-" in base:
            continue

        # Some eslint files deal with generateQI, so just ignore them.
        if "tools/lint/eslint/" in base:
            continue

        # This file contains a false positive generateQI, from a commit message.
        if fileName == ".hg-annotate-ignore-revs":
            continue

        # This is a patch file that causes a false positive.
        if fileName == "fluent.js.patch":
            continue

        if not base.endswith("/"):
            base += "/"
        fullFileName = base + fileName

        # Third party code is unlikely to use XPIDL, and it contains some false positives.
        if "/third_party/" in fullFileName:
            continue
        if "/other-licenses/" in fullFileName:
            continue

        if fileName.endswith(".idl"):
            # The WPT directory contains a number of WebIDL files with the extension .idl.
            if "/testing/web-platform" in base:
                continue
            # This is a WebIDL-ish file.
            if fullFileName.endswith("browser/components/translation/cld2/cld.idl"):
                continue
            # Some accessible subdirectories contains some Windows IDL files with the .idl extension.
            if "accessible/ipc/win/" in base:
                continue
            if "accessible/interfaces/" in fullFileName:
                if "/msaa" in fullFileName or "/gecko" in fullFileName or "/ia2" in fullFileName:
                    continue

            idlFileAnalyzer(args, fullFileName, jsImplementedInterfaces,
                            nonBuiltinInterfaces)
        else:
            generateQIFinder(args, fullFileName, jsImplementedInterfaces)


builtinClassable = list(nonBuiltinInterfaces - jsImplementedInterfaces)
builtinClassable.sort()


print "Interfaces that might be markable as builtinclass:"
for i in builtinClassable:
    print i
print
