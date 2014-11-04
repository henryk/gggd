#!/usr/bin/env python2.7
'''
Created on 3 Nov 2014

@author: henryk
'''
import os
import sys

def handle_file(filename):
    data = open(filename, "r").read()
    parts = data.split("\r\n\r\n", 2)
    if len(parts) < 3:
        print "Great error", filename
        return
    if parts[1].startswith("X-Google-Groups"):
        print filename,
        if len(parts[1]) > len(parts[0]):
            data = data[len(parts[0])+4:]
            print "OK"
        else:
            print "Nope"
    with open(filename + ".demangled", "w") as fp:
        fp.write( data )

if __name__ == '__main__':
    files = []
    for root, dirnames, filenames in os.walk(sys.argv[1]):
        files.extend(map(lambda a: os.path.join(root,a), filenames))
    for filename in files:
        handle_file(filename)