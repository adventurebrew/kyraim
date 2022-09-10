import csv
import glob

import operator
import os
from itertools import chain, groupby
from typing import IO, Iterable, Iterator, Sequence

from kyraim.codex.base import SupportsRead


def parse(stream: SupportsRead[bytes]) -> Iterator[bytes]:
    yield stream.read().removesuffix(b'\x1a')


def compose(
    lines: Iterable[Sequence[str]],
    target: str = 'book_patch',
    encoding: str = 'cp862',
) -> None:
    grouped = groupby(lines, key=operator.itemgetter(0))
    for tfname, group in grouped:
        basename = os.path.basename(tfname)
        lines_in_group = [line for _, line in group]

        assert len(lines_in_group) == 1, lines_in_group

        text = lines_in_group[0].replace('\n', '\r\n')

        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, basename), 'wb') as res:
            res.write(text.encode(encoding) + b'\x1a')


def write_parsed(
    filename: str,
    instream: IO[bytes],
    outstream: IO[str],
) -> None:
    for line in parse(instream):
        text = line.decode('cp862').replace('"', '""').replace('\r\n', '\n')
        # assert '\n' not in text
        print(os.path.basename(filename), f'"{text}"', sep='\t', file=outstream)


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
        with open('asis.tsv', 'w', encoding='utf-8') as out:
            for filename in files:
                with open(filename, 'rb') as stream:
                    write_parsed(filename, stream, out)
