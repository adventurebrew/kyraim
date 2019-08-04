import io
import logging

from contextlib import contextmanager
from itertools import chain

import pakfile

from typing import  Iterator, Iterable, Sequence, Tuple, TypeVar

T = TypeVar('T')
U = TypeVar('U')

PairIterator = Iterator[Tuple[T, U]]
PairIterable = Iterable[Tuple[T, U]]

logging.basicConfig(level=logging.DEBUG)

def write_uint32_le(number: int) -> bytes: 
    return number.to_bytes(4, byteorder='little', signed=False)

def calculate_index_length(pak_index: Sequence[str]) -> int:
    return sum(len(write_index_entry(fname, 0)) for fname in pak_index)

def write_index_entry(fname: str, offset: int) -> bytes:
    return write_uint32_le(offset) + fname.encode() + b'\00'

def generate_index(data_files: PairIterator[str, bytes]) -> PairIterator[bytes, bytes]:
    end = ('\00\00\00\00', b'')
    pak_index, rdata = zip(*chain(data_files, (end,)))
    off = calculate_index_length(pak_index)
    for fname, fdata in zip(pak_index, rdata):
        yield write_index_entry(fname, off), fdata
        off += len(fdata)

def read_file_fallback(pak: PairIterable[str, bytes], pakname: str) -> PairIterator[str, bytes]:
    for fname, data in pak:
        fpath = os.path.join(pakname, fname)
        if os.path.exists(fpath):
            logging.info(f'Adding {fpath}')
            with open(fpath, 'rb') as src:
                data = src.read()
        yield fname, data

if __name__ == "__main__":
    import os
    import glob
    import sys

    if len(sys.argv) < 2:
        print("Usage: pakfile.py PATH_TO_KYRANDIA")
        exit(1)

    # TODO: use argparse
    srcdir = sys.argv[1]
    kyrapath = sys.argv[2:]
    files = set(pakfile.flatten(glob.iglob(r) for r in kyrapath))
    for filename in files:
        dirname = os.path.basename(filename)
        with pakfile.open(filename) as pak:
            index, data = zip(*generate_index(read_file_fallback(pak, srcdir)))
        with open(os.path.join('out', dirname), 'wb') as output:
            output.write(b''.join(index))
            output.write(b''.join(data))
