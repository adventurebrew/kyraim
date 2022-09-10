#!/usr/bin/env python3

import os
import glob

from itertools import takewhile, chain
from functools import partial

from typing import Any, IO, Iterable, Sequence, Tuple

from kyraim.archive.base import ArchiveIndex, SimpleArchive, SimpleEntry, make_opener
from kyraim.codex.base import readcstr, read_uint32_le


GLOB_ALL = '*'


def read_index_entry(stream: IO[bytes]) -> Tuple[str, int]:
    return readcstr(stream).decode(), read_uint32_le(stream)


def before_offset(stream: IO[bytes], off: int, *args: Any) -> bool:
    return stream.tell() < off


def read_index_entries(stream: IO[bytes]) -> Tuple[Sequence[str], Sequence[int]]:
    off = read_uint32_le(stream)
    index_entries = iter(partial(read_index_entry, stream), ('', 0))
    index_entries = takewhile(partial(before_offset, stream, off), index_entries)
    names, offs = zip(*index_entries)
    return names, (off,) + tuple(offs)


def create_index_mapping(
    names: Iterable[str],
    offsets: Sequence[int],
) -> ArchiveIndex[SimpleEntry]:
    sizes = [(end - start) for start, end in zip(offsets, offsets[1:])]
    return dict(zip(names, zip(offsets, sizes)))


class PakFile(SimpleArchive):
    def _create_index(self) -> ArchiveIndex[SimpleEntry]:
        return create_index_mapping(*read_index_entries(self._stream))


open = make_opener(PakFile)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('files', nargs='+', help='files to extract')
    args = parser.parse_args()

    files = set(chain.from_iterable(glob.iglob(r) for r in args.files))
    print(files)
    for filename in files:
        dirname = os.path.basename(filename)
        with PakFile(filename) as pak:
            pak.extractall(dirname)
            if dirname == 'INTRO.VRM':
                with pak.open('INTROPAT.BAT', 'r') as bat:
                    print(''.join(bat))
