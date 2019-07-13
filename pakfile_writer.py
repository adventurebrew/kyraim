import io
import logging

from contextlib import contextmanager
from itertools import chain

import pakfile

from typing import Callable, Iterator, Iterable, Sequence, Tuple, TypeVar

F = TypeVar('F')
T = TypeVar('T')

logging.basicConfig(level=logging.DEBUG)

def write_uint32_le(number: int) -> bytes: 
    return number.to_bytes(4, byteorder='little', signed=False)

def calculate_index_length(pak_index: Sequence[str]) -> int:
    number_of_files = len(pak_index)
    return (number_of_files * 4) + sum(len(fname) + 1 for fname in pak_index) + 9

def write_index_entry(fname, offset) -> bytes:
    return write_uint32_le(offset) + fname.encode() + b'\00'

# def bind(fn: Callable[[F], T], fdata: F) -> Tuple[F, T]:
#     return fdata, fn(fdata)

# def pak_files(data_files: Iterator[Tuple[str, bytes]]) -> Tuple[Iterator[bytes], Iterable[bytes]]:
#     pak_index, rdata = zip(*data_files)
#     off = calculate_index_length(pak_index)
#     fnames = tuple(pak_index) + ('\00\00\00\00',)
#     rdata, lens = zip(*(bind(len, fdata) for fdata in rdata))
#     offsets = (off + sum(lens[:idx]) for idx, _ in enumerate(fnames))
#     index = (write_index_entry(fname, offset) for fname, offset in zip(fnames, offsets))
#     return index, rdata

def pak_files_gen(data_files: Iterator[Tuple[str, bytes]]) -> Iterator[Tuple[bytes, bytes]]:
    end = ('\00\00\00\00', b'')
    pak_index, rdata = zip(*data_files)
    off = calculate_index_length(pak_index)
    for fname, fdata in chain(zip(pak_index, rdata), (end,)):
        yield write_index_entry(fname, off), fdata
        off += len(fdata)

def read_file_fallback(pak: Iterable[Tuple[str, bytes]], pakname: str) -> Iterator[Tuple[str, bytes]]:
    for fname, data in pak:
        fpath = f'{pakname}/{fname}'
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
    kyrapath = sys.argv[1:]
    files = set(pakfile.flatten(glob.iglob(r) for r in kyrapath))
    for filename in files:
        dirname = os.path.basename(filename)
        with pakfile.open(filename) as pak:
            index, data = zip(*pak_files_gen(read_file_fallback(pak, dirname)))
        with open('result.pak', 'wb') as output:
            output.write(b''.join(index))
            output.write(b''.join(data))
