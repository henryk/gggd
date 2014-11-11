#!/usr/bin/env python2.7
'''
Created on 3 Nov 2014

@author: henryk
'''
from argparse import ArgumentParser
import sys
import email.parser

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

def fix_nested_mime(data):
    msg = email.parser.Parser().parsestr(data, headersonly=True)
    parts = data.split("\r\n")
    
    outer_boundary = msg.get_boundary()
    outer_content_type = msg.get_content_type()
    
    in_body = False
    last_was_boundary = False
    insert_at = None
    inner_boundary = None
    
    for n, l in enumerate(parts):
        if not in_body:
            if l == "":
                in_body = True
        else:
            if not last_was_boundary:
                if l == "--%s" % outer_boundary:
                    last_was_boundary = True
            else:
                last_was_boundary = False
                
                if insert_at is None:
                    if l.startswith("--"):
                        # This looks like a MIME boundary is following immediately after a boundary. 
                        # There is a very high chance that this was a part that had only a header and
                        # for reasons unknown was removed by Google. Insert a new header indicating the
                        # current line as a MIME boundary. We don't know the correct MIME type, but will
                        # apply a heuristic to guess it, based on the outer MIME type.
                        
                        insert_at = n
                        inner_boundary = l[2:]
                        break
    
    if insert_at is not None:
        guessed_content_type = None
        if outer_content_type == "multipart/mixed":
            guessed_content_type = "multipart/alternative"
        elif outer_content_type == "multipart/related":
            guessed_content_type = "multipart/alternative"
        elif outer_content_type == "multipart/alternative":
            guessed_content_type = "multipart/mixed"
        elif outer_content_type == "multipart/signed":
            guessed_content_type = "multipart/mixed"
        
        if guessed_content_type is None:
            raise ProcessingError("Unknown outer MIME content type %s, couldn't guess nested MIME type" % outer_content_type)
        
        parts.insert(insert_at, "Content-Type: %s; " % guessed_content_type)
        parts.insert(insert_at+1, '  boundary="%s"' % inner_boundary)
        parts.insert(insert_at+2, "")
        data = "\r\n".join(parts)
    
    return data

OPERATORS = [process_multiple_headers, fix_nested_mime]

def handle_data(data):
    for op in OPERATORS:
        try:
            data = op(data)
        except ProcessingError as e:
            e.message = "%s: %s" % (op.__name__, e.message)
            raise
    return data

def handle_file(filename, in_place, suffix, dry_run):
    if not filename is None:
        data = open(filename, "r").read()
        stdin = False
    else:
        data = sys.stdin.read()
        stdin = True
        filename = "<stdin>"
    
    # Allow to operate on local unix files
    if len(data.split("\r\n")) < 10 and len(data.split("\n")) > 10:
        converted_line_endings = True
        data = "\r\n".join( data.split("\n") )
    else:
        converted_line_endings = False
    
    try:
        data = handle_data(data)
    except ProcessingError as e:
        print >>sys.stderr, "%s: %s" % (filename, e.message)
    
    if converted_line_endings:
        data = "\n".join( data.split("\r\n") )
    
    if not dry_run:
        if stdin:
            sys.stdout.write( data )
        else:
            if in_place:
                out_name = filename
            else:
                out_name = filename + suffix
            with open(out_name, "w") as fp:
                fp.write( data )

def main():
    parser = ArgumentParser()
    parser.add_argument('-V', '--version', action='version', version="v%s" % __version__)
    parser.add_argument("-i", '--in-place', action="store_true", help="Demangle files in-place (possibly dangerous) [default: %(default)s]")
    parser.add_argument("-s", '--suffix', help="Suffix for demangled files, when not operating in-place [default: %(default)s]", default=".demangled")
    parser.add_argument("-n", '--dry-run', help="Don't actually write anything", action="store_true")
    parser.add_argument(dest="file", help="Name of the message file(s) to demangle", metavar="file", nargs="*")

    # Process arguments
    args = parser.parse_args()
    
    if len(args.file) == 0: args.file.append(None) 
    
    for f in args.file:
        try:
            handle_file(f, args.in_place, args.suffix, args.dry_run)
        except Exception as e:
            print >>sys.stderr, "%s: %s" % (f, e)


if __name__ == '__main__':
    main()
