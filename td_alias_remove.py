#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Analyze the need for includes of nsRefPtr.h vs nsAutoPtr.h

import re
import os
import argparse


tdAliases = """
  TD_ALIAS_(T_I8, TD_INT8);
  TD_ALIAS_(T_I16, TD_INT16);
  TD_ALIAS_(T_I32, TD_INT32);
  TD_ALIAS_(T_I64, TD_INT64);
  TD_ALIAS_(T_U8, TD_UINT8);
  TD_ALIAS_(T_U16, TD_UINT16);
  TD_ALIAS_(T_U32, TD_UINT32);
  TD_ALIAS_(T_U64, TD_UINT64);
  TD_ALIAS_(T_FLOAT, TD_FLOAT);
  TD_ALIAS_(T_DOUBLE, TD_DOUBLE);
  TD_ALIAS_(T_BOOL, TD_BOOL);
  TD_ALIAS_(T_CHAR, TD_CHAR);
  TD_ALIAS_(T_WCHAR, TD_WCHAR);
  TD_ALIAS_(T_VOID, TD_VOID);
  TD_ALIAS_(T_NSIDPTR, TD_NSIDPTR);
  TD_ALIAS_(T_CHAR_STR, TD_PSTRING);
  TD_ALIAS_(T_WCHAR_STR, TD_PWSTRING);
  TD_ALIAS_(T_INTERFACE, TD_INTERFACE_TYPE);
  TD_ALIAS_(T_INTERFACE_IS, TD_INTERFACE_IS_TYPE);
  TD_ALIAS_(T_LEGACY_ARRAY, TD_LEGACY_ARRAY);
  TD_ALIAS_(T_PSTRING_SIZE_IS, TD_PSTRING_SIZE_IS);
  TD_ALIAS_(T_PWSTRING_SIZE_IS, TD_PWSTRING_SIZE_IS);
  TD_ALIAS_(T_UTF8STRING, TD_UTF8STRING);
  TD_ALIAS_(T_CSTRING, TD_CSTRING);
  TD_ALIAS_(T_ASTRING, TD_ASTRING);
  TD_ALIAS_(T_NSID, TD_NSID);
  TD_ALIAS_(T_JSVAL, TD_JSVAL);
  TD_ALIAS_(T_DOMOBJECT, TD_DOMOBJECT);
  TD_ALIAS_(T_PROMISE, TD_PROMISE);
  TD_ALIAS_(T_ARRAY, TD_ARRAY);
"""



def getAliases():
    aliasPatt = re.compile('TD_ALIAS_\(([^,]+), ([^)]+)\)')
    replacements = []
    befores = []
    for l in tdAliases.splitlines():
        aliasMatch = aliasPatt.search(l)
        if not aliasMatch:
            continue
        before = "nsXPTType::" + aliasMatch.group(1)
        after = aliasMatch.group(2)
        replacements.append([before, after])
        befores.append(before)
    beforeRe = re.compile('|'.join(befores))

    # T_INTERFACE is a prefix of T_INTERFACE_IS, but TD_INTERFACE_TYPE
    # is not a prefix of TD_INTERFACE_IS_TYPE. This means we have to
    # substitute T_INTERFACE_IS first. To work around this general problem,
    # we sort the replacements from longest to shortest.
    replacements = sorted(replacements, reverse=True, key=lambda x: len(x[0]))
    for x in replacements:
        print(f'{x[0]} --> {x[1]}')

    return [beforeRe, replacements]


def fileAnalyzer(args, fname, beforeRe, replacements):
    f = open(fname, "r")

    if args.fixFiles:
        tempFileName = fname + ".intermediate"
        anyFixed = False
        newFile = open(tempFileName, "w")

    for l in f:
        m = beforeRe.search(l)
        if m:
            foundReplacement = False
            new = l
            for [before, after] in replacements:
                new = l.replace(before, after)
                if new != l:
                    print(f'Changed line "{l[:-1]}" to "{new[:-1]}"')
                    anyFixed = True
                    foundReplacement = True
                    break
            assert foundReplacement
            assert new != l
            if args.fixFiles:
                newFile.write(new)
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


def directoryAnalyzer(args):
  aliasInfo = getAliases()
  beforeRe = aliasInfo[0]
  replacements = aliasInfo[1]

  for (base, _, files) in os.walk(args.directory):
      for fileName in files:
          if not (fileName.endswith('.h') or fileName.endswith('.cpp')):
              continue

          if not base.endswith("/"):
              base += "/"
          fullFileName = base + fileName

          fileAnalyzer(args, fullFileName, beforeRe, replacements)


# Need to run this on js/xpconnect and xpcom/

parser = argparse.ArgumentParser(description='Replacing TD_ALIAS')
parser.add_argument('directory', metavar='D',
                    help='Full path of directory to open files from')

parser.add_argument('--fix', dest='fixFiles', action='store_true',
                    help='Fix any errors that are found')

args = parser.parse_args()

directoryAnalyzer(args)
