#!/usr/bin/env python3

import sys
import os
import errno
from struct import Struct
from time import time
from itertools import takewhile
import glob

uint32_le = Struct('<I')
read_uint32_le = lambda f: uint32_le.unpack(f.read(uint32_le.size))[0]
flatten = lambda l: (item for sublist in l for item in sublist)

def readcstr(f):
    return ''.join(iter(lambda: f.read(1).decode(), '\00'))

def create_directory(name):
    try:
        os.makedirs(name)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def read_index(f):
    off = read_uint32_le(f)
    read_both = iter(lambda: (readcstr(f), read_uint32_le(f)), ('', 0))
    pred = lambda _: f.tell() < off
    names, offs = zip(*takewhile(pred, read_both))
    return names, [off] + list(offs)

def read_file(f, off, size):
    f.seek(off) # need unit test to check offset is always equal to f.tell()
    return f.read(size)

def extract_all(f):
    with open(f, 'rb') as vrmFile:
        names, offsets = read_index(vrmFile)
        sizes = [end - start for start, end in zip(offsets, offsets[1:])]
        contents = (read_file(vrmFile, off, size) for off, size in zip(offsets, sizes))
        for name, data in zip(names, contents):
            yield name, data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: vrm.py PATH_TO_KYRANDIA")
        exit(1)

    # TODO: use argparse
    kyrapath = sys.argv[1:]
    files = set(flatten(glob.iglob(r) for r in kyrapath))
    for filename in files:
        dirname = os.path.basename(filename)
        create_directory(dirname)
        files_in_vrm = extract_all(filename)
        for fn, data in files_in_vrm:
            with open(os.path.join(dirname, fn), 'wb') as outFile:
                outFile.write(data)
