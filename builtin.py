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
    "extIWebNavigation",
]
weirdInterfacesToIgnorePatt = re.compile("^" + "|".join(weirdInterfacesToIgnore) + "$")

def assertInterfaceOkay(fname, interface):
    if okayInterfacePatt.match(interface):
        return
    if weirdInterfacesToIgnorePatt.match(interface):
        return
    raise Exception("Bad interface " + interface + " in file " + fname)

# Searching for the entire ChromeUtils.generateQI seems reasonable:
# https://searchfox.org/mozilla-central/search?q=%5B%5Es%5D.generateqi&path=&case=false&regexp=true

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


forwardDeclPatt = re.compile("^interface [A-Za-z0-9_-]+;$")

# Look at XPIDL files for interfaces that are implementable by JS.
def idlFileAnalyzer(args, fname, maybeBuiltinables):
    f = open(fname, "r")
    prevLine = None

    for l in f:
        l = l.strip()
        if l.startswith("//"):
            continue
        if not l.startswith("interface "):
            prevLine = l
            continue
        # Just a forward declaration. Ignore it.
        if forwardDeclPatt.match(l):
            prevLine = None
            continue
        interface = l.split()[1].strip(":")
        assertInterfaceOkay(fname, interface)

        attributes = prevLine.strip().strip("[]").split(",")
        attributes = list(map(lambda l: l.strip(), attributes))
        scriptable = False
        builtinClass = False
        function = False
        anyUUID = False
        for a in attributes:
            if a == 'scriptable':
                scriptable = True
            if a == 'builtinclass':
                builtinClass = True
                continue
            if a == 'function':
                function = True
                continue
            if a.startswith('uuid'):
                assert not anyUUID
                anyUUID = True
                continue
        if not anyUUID:
            print fname, prevLine
        # Assert we found a UUID to guard against bugs in our crude parser.
        assert anyUUID

        # It doesn't make sense to mark non-scriptable interfaces builtinclass.
        assert scriptable or not builtinClass

        # If something isn't scriptable, we don't want to make it builtinclass.
        # If something is already builtinclass, we don't want to make it builtinclass.
        # If something is a function, we can't analyze whether it is used by JS.
        if scriptable and not builtinClass and not function:
            maybeBuiltinables.setdefault(interface, []).append(fname)


    f.close()




parser = argparse.ArgumentParser(description='Find XPIDL interfaces that could be marked builtinclass')
parser.add_argument('directory', metavar='D',
                    help='Full path of directory to open files from')

parser.add_argument('--showdir', dest='showDir', action='store_true',
                    help='show the directory the IDL file is located in')

args = parser.parse_args()

jsImplementedInterfaces = set([])
maybeBuiltinables = {}

validExtensions = [".sys.mjs", ".jsm", ".js", ".xhtml", ".html", ".sjs", ".idl"]
validFileRe = re.compile("^.*(?:" + '|'.join(map(lambda e: "(?:" + re.escape(e) + ")", validExtensions)) + ")$")

for (base, _, files) in os.walk(args.directory):
    for fileName in files:
        # Using a regexp seems like it is slightly slower but whatever.
        if not(validFileRe.match(fileName)):
            continue

        #if fileName.endswith('.cpp') or fileName.endswith('.h') or fileName.endswith('~'):
        #    continue

        # XXX Hacky way to not process files in the objdir.
        if "obj-" in base:
            continue

        if ".git" in base or ".hg" in base:
            continue

        # Some eslint files deal with generateQI, so just ignore them.
        if "tools/lint/eslint/" in base:
            continue

        # There are a lot of these files, and they don't use generateQI.
        if "testing/web-platform/" in base:
            continue
        if "js/src/tests/" in base:
            continue

        # These files contain a false positive generateQI, from a commit message.
        if fileName == ".hg-annotate-ignore-revs":
            continue
        if fileName == ".git-blame-ignore-revs":
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
            # This is a WebIDL-ish file.
            if fullFileName.endswith("toolkit/components/translation/cld2/cld.idl"):
                continue
            # Some accessible subdirectories contains some Windows IDL files with the .idl extension.
            if "accessible/ipc/win/" in base:
                continue
            if "accessible/interfaces/" in fullFileName:
                if "/msaa" in fullFileName or "/gecko" in fullFileName or "/ia2" in fullFileName:
                    continue

            idlFileAnalyzer(args, fullFileName, maybeBuiltinables)
        else:
            generateQIFinder(args, fullFileName, jsImplementedInterfaces)

# XXX Also need to take into account the handful of do_ImportModule interfaces.

# XXX It seems like a static analysis is doomed, because you can just pass in
# random JS objects to XPCOM and it is fine with not having a QI?
# An example of this is nsIWorkerDebuggerManagerListener which is used as
# an argument to nsIWorkerDebuggerManager, and some random JS object gets passed in.

builtinClassable = set(maybeBuiltinables.keys()) - jsImplementedInterfaces


if not args.showDir:
    output = list(builtinClassable)
else:
    baseDirLen = len(args.directory)
    output = []
    for i in builtinClassable:
        for baseIdir in maybeBuiltinables[i]:
            idir = baseIdir[baseDirLen:]
            idir = idir[:idir.rfind("/")]
            output.append(idir + " " + i)


output.sort()
print "Interfaces that might be markable as builtinclass:"
for i in output:
    print i
print
