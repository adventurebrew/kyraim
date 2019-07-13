#!/usr/bin/env python3

import builtins
import io
import sys
import os
import glob

from contextlib import contextmanager
from collections import OrderedDict
from itertools import takewhile
from functools import partial

from typing import Any, AnyStr, Callable, ContextManager, IO, Iterator, Iterable, List, Mapping, Sequence, Tuple, TypeVar, Union

PakIndex = Mapping[str, Tuple[int, int]]
T = TypeVar('T')

# from struct import Struct
# uint32_le = Struct('<I')
# def read_uint32_le(f): 
#     return uint32_le.unpack(f.read(uint32_le.size))[0]

def read_uint32_le(stream: IO[bytes]) -> int: 
    return int.from_bytes(stream.read(4), byteorder='little', signed=False)

def flatten(ls: Iterable[Iterable[T]]) -> Iterator[T]: 
    return (item for sublist in ls for item in sublist)

def readcstr(stream: IO[bytes]) -> str:
    return ''.join(iter(lambda: stream.read(1).decode(), '\00'))

def create_directory(name: AnyStr) -> None:
    os.makedirs(name, exist_ok=True)

def read_index_entry(stream: IO[bytes]) -> Tuple[str, int]:
    return readcstr(stream), read_uint32_le(stream)

def before_offset(stream: IO[bytes], off: int, *args: Any) -> bool:
    return stream.tell() < off

def read_index_entries(stream: IO[bytes]) -> Tuple[Sequence[str], Sequence[int]]:
    off = read_uint32_le(stream)
    index_entries = iter(partial(read_index_entry, stream), ('', 0))
    index_entries = takewhile(partial(before_offset, stream, off), index_entries)
    names, offs = zip(*index_entries)
    return names, (off,) + tuple(offs)

def read_file(stream: IO[bytes], off: int, size: int) -> bytes:
    stream.seek(off, io.SEEK_SET) # need unit test to check offset is always equal to f.tell()
    return stream.read(size)

def create_index_mapping(names: Iterable[str], offsets: Sequence[int]) -> PakIndex:
    sizes = [(end - start) for start, end in zip(offsets, offsets[1:])]
    return OrderedDict(zip(names, zip(offsets, sizes)))

class PakFile:
    _stream: IO[bytes]

    filename: Union[str, bytes] 
    index: PakIndex

    def __init__(self, filename: AnyStr) -> None:
        self.filename = filename
        self._stream = builtins.open(self.filename, 'rb')
        self.index = create_index_mapping(*read_index_entries(self._stream))

    def __enter__(self):
        return self

    @contextmanager
    def open(self, fname: str, mode: str = 'r') -> Iterator[IO]:
        if not fname in self.index:
            raise ValueError(f'no member {fname} in pakfile')

        start, size = self.index[fname]
        with builtins.open(self.filename, 'rb') as f:
            data = read_file(f, start, size)

        stream: IO
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

    def extractall(self, dirname: str) -> None:
        create_directory(dirname)
        for fname, filedata in self:
            with builtins.open(os.path.join(dirname, fname), 'wb') as out_file:
                out_file.write(filedata)

@contextmanager
def open(*args: Any, **kwargs: Any) -> Iterator[PakFile]:
    yield PakFile(*args, **kwargs)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: pakfile.py PATH_TO_KYRANDIA")
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
