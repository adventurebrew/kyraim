import binascii
import csv
import glob

import operator
import os
from itertools import chain, groupby
from typing import IO, Iterable, Iterator, Sequence, Tuple

from kyraim.codex.base import read_uint16_le, readcstr, write_uint16_le


def parse(stream: IO[bytes]) -> Iterator[Tuple[int, bytes, bytes]]:
    table_entries = read_uint16_le(stream)
    index_table = [read_uint16_le(stream) for _ in range(table_entries)]
    offsets = [read_uint16_le(stream) for _ in range(table_entries)]
    for idx, off in zip(index_table, offsets):
        meta = stream.read(off - stream.tell())
        assert stream.tell() == off, (stream.tell(), off)
        line = readcstr(stream)
        yield idx, line, meta


def compose(
    lines: Iterable[Sequence[str]],
    target: str = 'tre_patch',
    encoding: str = 'cp862',
) -> None:
    grouped = groupby(lines, key=operator.itemgetter(0))
    for tfname, group in grouped:
        basename = os.path.basename(tfname)
        _, idcs, hmetas, outs = zip(*group)
        texts = [
            out.replace('`', '"').encode(encoding) + b'\0'
            for out in outs
        ]
        num_entries = len(texts)
        first_off = 2 + (num_entries) * 4

        metas = [binascii.unhexlify(meta) for meta in hmetas]

        offs = bytearray()
        for meta, entry in zip(metas, texts):
            first_off += len(meta)
            offs += write_uint16_le(first_off)
            first_off += len(entry)

        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, basename), 'wb') as res:
            res.write(
                write_uint16_le(num_entries)
                + b''.join(write_uint16_le(int(idx)) for idx in idcs)
                + bytes(offs)
                + b''.join(meta + text for meta, text in zip(metas, texts))
            )


def write_parsed(
    filename: str,
    instream: IO[bytes],
    outstream: IO[str],
) -> None:
    for idx, line, meta in parse(instream):
        text = line.decode('cp862').replace('"', '""')
        assert '\n' not in text
        print(os.path.basename(filename), idx, meta.hex(), f'"{text}"', sep='\t', file=outstream)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('files', nargs='+', help='files to extract')
    parser.add_argument('--encode', '-e', action='store_true', help='files to extract')
    parser.add_argument('--decode', '-d', action='store_true', help='files to extract')
    args = parser.parse_args()

    files = sorted(set(chain.from_iterable(glob.iglob(r) for r in args.files)))
    print(files)
    if args.encode:
        for filename in files:
            with open(filename, 'r', encoding='utf-8') as f:
                tsv_file = csv.reader(f, delimiter='\t')
                compose(tsv_file)
    if args.decode:
        with open('tre.tsv', 'w', encoding='utf-8') as out:
            for filename in files:
                with open(filename, 'rb') as stream:
                    write_parsed(filename, stream, out)
