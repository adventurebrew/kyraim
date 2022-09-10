import glob
import io
import os
from itertools import chain
from typing import IO

from kyraim.archive.base import ArchiveIndex, BaseArchive, make_opener
from kyraim.codex.base import read_uint32_le


def read_index_entries(stream: IO[bytes]) -> ArchiveIndex:
    _unk = stream.read(3)
    size = read_uint32_le(stream)
    subs = stream.read(size).split(b'\r\n')[:-1]
    index = {}
    for i in subs:
        size = read_uint32_le(stream)
        offset = stream.tell()
        index[os.path.basename(i).decode('ascii')] = (offset, size)
        stream.seek(size, io.SEEK_CUR)
    rest = stream.read()
    assert not rest, rest
    return index


class WestwoodInstaller(BaseArchive):
    def create_index(self) -> ArchiveIndex:
        return read_index_entries(self._stream)


open = make_opener(WestwoodInstaller)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('files', nargs='+', help='files to extract')
    args = parser.parse_args()

    files = set(chain.from_iterable(glob.iglob(r) for r in args.files))
    print(files)
    for filename in files:
        dirname = os.path.basename(filename)
        with WestwoodInstaller(filename) as inst:
            inst.extractall(dirname)
