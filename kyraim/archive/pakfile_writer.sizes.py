import logging
from itertools import chain
from typing import Iterator, Iterable, Mapping, Sequence, Tuple, TypeVar

from kyraim.archive import pakfile
from kyraim.codex.base import write_uint32_le

T = TypeVar('T')
U = TypeVar('U')

PairIterator = Iterator[Tuple[T, U]]
PairIterable = Iterable[Tuple[T, U]]

logging.basicConfig(level=logging.DEBUG)


def calculate_index_length(pak_index: Sequence[str]) -> int:
    return sum(len(write_index_entry(fname, 0)) for fname in pak_index)


def write_index_entry(fname: str, offset: int) -> bytes:
    return write_uint32_le(offset) + fname.encode() + b'\00'


def generate_index(data_files: PairIterable[str, int]) -> Iterator[bytes]:
    end = ('\00\00\00\00', 0)
    pak_index, lns = zip(*chain(data_files, (end,)))
    off = calculate_index_length(pak_index)
    for fname, size in zip(pak_index, lns):
        yield write_index_entry(fname, off)
        off += size


def read_index(index: PairIterable[str, int], pakname: str) -> PairIterator[str, int]:
    for fname, size in index:
        fpath = os.path.join(pakname, fname)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
        yield fname, size


def read_data(index: PairIterable[str, bytes], pakname: str) -> Iterator[bytes]:
    for fname, data in index:
        fpath = os.path.join(pakname, fname)
        if os.path.exists(fpath):
            logging.info(f'Adding {fpath}')
            with open(fpath, 'rb') as src:
                data = src.read()
        yield data


def extract_sizes(index: Mapping[str, Tuple[int, int]]) -> PairIterator[str, int]:
    return ((fname, size) for fname, (_, size) in index.items())


if __name__ == '__main__':
    import os
    import glob
    import sys

    if len(sys.argv) < 2:
        print('Usage: pakfile.py PATH_TO_KYRANDIA')
        exit(1)

    # TODO: use argparse
    kyrapath = sys.argv[1:]
    files = sorted(set(chain.from_iterable(glob.iglob(r) for r in kyrapath)))
    for filename in files:
        dirname = os.path.basename(filename)
        with pakfile.open(filename) as pak:
            file_sizes = extract_sizes(pak.index)
            with open('result.pak', 'wb') as output:
                output.write(b''.join(generate_index(read_index(file_sizes, dirname))))
                output.write(b''.join(read_data(pak, dirname)))
