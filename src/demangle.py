#!/usr/bin/env python2.7
'''
Created on 3 Nov 2014

@author: henryk
'''
from argparse import ArgumentParser
import sys

__version__ = 0.1

class ProcessingError(Exception): pass

def process_multiple_headers(data):
    parts = data.split("\r\n\r\n", 2)
    if len(parts) < 3:
        raise ProcessingError("Malformed message")
    if parts[1].startswith("X-Google-Groups"):
        if len(parts[1]) > len(parts[0]):
            data = data[len(parts[0])+4:]
    return data

OPERATORS = [process_multiple_headers]

def handle_file(filename, in_place, suffix):
    if not filename is None:
        data = open(filename, "r").read()
        stdin = False
    else:
        data = sys.stdin.read()
        stdin = True
        filename = "<stdin>"
    
    try:
        for op in OPERATORS:
            data = op(data)
    except ProcessingError as e:
        print >>sys.stderr, "%s: %s: %s" % (filename, op.__name__, e.message)
    
    if not stdin:
        with open(filename + suffix, "w") as fp:
            fp.write( data )
    else:
        sys.stdout.write( data )

def main():
    parser = ArgumentParser()
    parser.add_argument('-V', '--version', action='version', version="v%s" % __version__)
    parser.add_argument("-i", '--in-place', type=bool, help="Demangle files in-place (possibly dangerous) [default: %(default)s]", default=False)
    parser.add_argument("-s", '--suffix', help="Suffix for demangled files, when not operating in-place [default: %(default)s]", default=".demangled")
    parser.add_argument(dest="file", help="Name of the message file(s) to demangle", metavar="file", nargs="*")

    # Process arguments
    args = parser.parse_args()
    
    if len(args.file) == 0: args.file.append(None) 
    
    for f in args.file:
        try:
            handle_file(f, args.in_place, args.suffix)
        except Exception as e:
            print >>sys.stderr, "%s: %s" % (f, e)


if __name__ == '__main__':
    main()
