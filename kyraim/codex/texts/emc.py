import csv
import glob

from chunk import Chunk
from itertools import chain, takewhile
from functools import partial
import itertools
import operator
import os
import re
from typing import IO, Iterable, Iterator, Sequence, cast

from kyraim.codex.base import (
    SupportsRead,
    read_uint16_be,
    readcstr,
    write_uint16_be,
    write_uint32_be,
)


def read_chunks(stream: SupportsRead[bytes], **kwargs) -> Iterator[Chunk]:
    while True:
        try:
            chunk = Chunk(cast(IO[bytes], stream), **kwargs)
        except EOFError:
            break
        yield chunk
        chunk.skip()


def before_offset(stream: SupportsRead[bytes], offset: int, *args) -> bool:
    return stream.tell() <= offset


def parse(stream: SupportsRead[bytes]) -> Iterator[bytes]:
    form = Chunk(cast(IO[bytes], stream))
    assert form.getname() == b'FORM'
    assert form.read(4) == b'EMC2'
    for chunk in read_chunks(form):
        chunk.seek(0)
        if chunk.getname() == b'TEXT':
            start = read_uint16_be(chunk)
            read_offsets = iter(partial(read_uint16_be, chunk), b'')
            offs = list(takewhile(partial(before_offset, chunk, start), read_offsets))
            chunk.seek(-2, 1)
            assert chunk.tell() == start
            assert offs == sorted(offs)
            for off in chain([start], offs):
                # assert chunk.tell() == off, (chunk.tell(), off)
                chunk.seek(off)
                yield readcstr(chunk)


def wrap_chunk(tag: bytes, data: bytes, size_fix: int = 0):
    return tag + write_uint32_be(len(data) + size_fix) + data


VERIFY = True


def compose(
    lines: Iterable[Sequence[str]],
    target: str = 'patch',
    encoding: str = 'cp862',
) -> None:
    grouped = itertools.groupby(lines, key=operator.itemgetter(0))
    for fname, group in grouped:
        lines_in_group = [line for _, line in group]
        nfname = os.path.join(target, fname)
        os.makedirs(os.path.dirname(nfname), exist_ok=True)
        print(nfname, lines_in_group)

        data = bytearray(b'EMC2')
        with open(os.path.join('orig', fname), 'rb') as orig, open(nfname, 'wb') as out:
            form = Chunk(orig)
            assert form.getname() == b'FORM'
            assert form.read(4) == b'EMC2'
            for chunk in read_chunks(form):
                chunk.seek(0)
                if chunk.getname() == b'TEXT':
                    start = read_uint16_be(chunk)
                    read_offsets = iter(partial(read_uint16_be, chunk), b'')
                    orig_offs = list(
                        takewhile(partial(before_offset, chunk, start), read_offsets)
                    )

                    for off in chain([start], orig_offs):
                        chunk.seek(off)
                        print('ORIG', fname, f'{readcstr(chunk)!r}', sep='\t')

                    base = len(lines_in_group) * 2

                    if VERIFY:
                        assert base == start, (base, start)

                    text = '\0'.join(lines_in_group)
                    print([repr(line) for line in lines_in_group])
                    offs = [base] + [
                        m.start() + base + 1 for m in re.finditer('\0', text)
                    ]
                    print(offs)
                    print(text)

                    if VERIFY:
                        assert [start] + orig_offs == offs, ([start] + orig_offs, offs)

                    chunk_data = (
                        b''.join(write_uint16_be(off) for off in offs)
                        + text.replace('\n', '\r').encode(encoding)
                        + b'\0'
                    )

                    data += wrap_chunk(b'TEXT', chunk_data)

                    if len(data) % 2:
                        data += b'\0'
                else:
                    data += wrap_chunk(chunk.getname(), chunk.read())
                    if len(data) % 2:
                        data += b'\0'
                    # start = read_uint16_be(chunk)
                    # read_offsets = iter(partial(read_uint16_be, chunk), b'')
                    # offs = list(takewhile(partial(before_offset, chunk, start), read_offsets))
                    # assert offs == sorted(offs), offs
                    # for off in chain([start], offs):
                    #     # assert chunk.tell() == off, (chunk.tell(), off)
                    #     chunk.seek(off)
                    #     print(fname, f'"{readcstr(chunk)}"', sep='\t')
            idata = bytes(data)
            final_data = wrap_chunk(b'FORM', idata, 8)
            out.write(final_data)
            if VERIFY:
                form.seek(0)
                orig_data = form.read()
                if orig_data != idata:
                    for i in range(500):
                        left, right = orig_data[50 * i :][:50], idata[50 * i :][:50]
                        if left != right:
                            print('DIFF', left, right)
                        else:
                            if left:
                                print(left)
                    print('exiting...')
                    exit(1)
                assert orig_data == idata, repr(orig_data) + '\n' + repr(idata)
                orig.seek(0)
                orig_complete = orig.read()
                assert final_data == orig_complete, (
                    final_data[:12],
                    orig_complete[:12],
                )


def write_parsed(
    filename: str,
    instream: IO[bytes],
    outstream: IO[str],
) -> None:
    for line in parse(instream):
        text = line.decode('cp862').replace('"', '""')
        assert '\n' not in text
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
        with open('emc.tsv', 'w', encoding='utf-8') as out:
            for filename in files:
                with open(filename, 'rb') as stream:
                    write_parsed(filename, stream, out)
