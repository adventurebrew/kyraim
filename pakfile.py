#!/usr/bin/env python3

import builtins
import sys
import os
from itertools import takewhile
import glob
from contextlib import contextmanager
from collections import OrderedDict


# from struct import Struct
# uint32_le = Struct('<I')
# def read_uint32_le(f): 
#     return uint32_le.unpack(f.read(uint32_le.size))[0]

def read_uint32_le(f): 
    return int.from_bytes(f.read(4), byteorder='little', signed=False)

def flatten(l): 
    return (item for sublist in l for item in sublist)

def readcstr(f):
    return ''.join(iter(lambda: f.read(1).decode(), '\00'))

def create_directory(name):
    os.makedirs(name, exist_ok=True)

def read_index(f):
    off = read_uint32_le(f)
    read_both = iter(lambda: (readcstr(f), read_uint32_le(f)), ('', 0))
    pred = lambda _: f.tell() < off
    names, offs = zip(*takewhile(pred, read_both))
    return names, [off] + list(offs)

def read_file(f, off, size):
    f.seek(off) # need unit test to check offset is always equal to f.tell()
    return f.read(size)

class PakFile:
    def __init__(self, filename):
        self.filename = filename
        self._pakfile = builtins.open(self.filename, 'rb')
        names, offsets = read_index(self._pakfile)
        sizes = [end - start for start, end in zip(offsets, offsets[1:])]
        self.index = OrderedDict(zip(names, zip(offsets, sizes)))

    def __enter__(self):
        return self

    @contextmanager
    def open(self, fname, mode='r'):
        import io
        if not fname in self.index:
            raise ValueError()
        
        start, size = self.index[fname]
        with builtins.open(self.filename, 'rb') as f:
            f.seek(start)
            data = f.read(size)
        with io.BytesIO(data) as stream:
            if not 'b' in mode:
                stream = io.TextIOWrapper(stream, encoding='utf-8')
            yield stream

    def __exit__(self, type, value, traceback):
        return self._pakfile.close()

    def __iter__(self):
        with builtins.open(self.filename, 'rb') as f:
            for fname, (start, size) in self.index.items():
                yield fname, read_file(f, start, size)

    def extractall(self, dirname):
        create_directory(dirname)
        for fname, filedata in self:
            with builtins.open(os.path.join(dirname, fname), 'wb') as outFile:
                outFile.write(filedata)

@contextmanager
def open(*args, **kwargs):
    yield PakFile(*args, **kwargs)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: vrm.py PATH_TO_KYRANDIA")
        exit(1)

    # TODO: use argparse
    kyrapath = sys.argv[1:]
    files = set(flatten(glob.iglob(r) for r in kyrapath))
    for filename in files:
        dirname = os.path.basename(filename)
        with PakFile(filename) as pak:
            pak.extractall(dirname)
            if dirname == 'INTRO.VRM':
                with pak.open('INTROPAT.BAT', 'r') as bat:
                    print(''.join(bat))
