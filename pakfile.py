#!/usr/bin/env python3

import builtins
import sys
import os
import glob

from contextlib import contextmanager
from collections import OrderedDict
from itertools import takewhile
from functools import partial

from typing import Any, AnyStr, Callable, IO, Iterator, List, Mapping, Tuple, Union

# from struct import Struct
# uint32_le = Struct('<I')
# def read_uint32_le(f): 
#     return uint32_le.unpack(f.read(uint32_le.size))[0]

def read_uint32_le(stream: IO[bytes]): 
    return int.from_bytes(stream.read(4), byteorder='little', signed=False)

def flatten(ls: Iterator[Iterator[Any]]) -> Iterator[Any]: 
    return (item for sublist in ls for item in sublist)

def readcstr(stream: IO[bytes]):
    return ''.join(iter(lambda: stream.read(1).decode(), '\00'))

def create_directory(name: AnyStr):
    os.makedirs(name, exist_ok=True)

def read_index_entry(stream: IO[bytes]) -> Tuple[str, int]:
    return readcstr(stream), read_uint32_le(stream)

def before_offset(stream: IO[bytes], off: int, *args: Any) -> bool:
    return stream.tell() < off

def read_index(stream: IO[bytes]):
    off = read_uint32_le(stream)
    index_entries = iter(partial(read_index_entry, stream), ('', 0)) # type: Iterator[Tuple[str, int]]
    index_entries = takewhile(partial(before_offset, stream, off), index_entries)
    names, offs = zip(*index_entries)
    return names, [off] + list(offs)

def read_file(stream: IO[bytes], off: int, size: int) -> bytes:
    stream.seek(off) # need unit test to check offset is always equal to f.tell()
    return stream.read(size)

class PakFile:
    def __init__(self, filename: AnyStr) -> None:
        self.filename: Union[str, bytes] = filename
        self._stream: IO[bytes] = builtins.open(self.filename, 'rb')
        names, offsets = read_index(self._stream)
        sizes: List[int] = [end - start for start, end in zip(offsets, offsets[1:])]
        self.index = OrderedDict(zip(names, zip(offsets, sizes))) # type: Mapping[str, Tuple[int, int]]

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
        return self._stream.close()

    def __iter__(self) -> Iterator[Tuple[str, bytes]]:
        with builtins.open(self.filename, 'rb') as f:
            for fname, (start, size) in self.index.items():
                yield fname, read_file(f, start, size)

    def extractall(self, dirname) -> None:
        create_directory(dirname)
        for fname, filedata in self:
            with builtins.open(os.path.join(dirname, fname), 'wb') as out_file:
                out_file.write(filedata)

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
