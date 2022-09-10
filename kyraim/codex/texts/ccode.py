import csv
import glob

import operator
import os
import re
from itertools import chain, groupby
from typing import IO, Callable, Iterable, Iterator, List, Sequence, cast

from kyraim.codex.base import (
    SupportsRead,
    collect,
    read_uint16_le,
    readcstr,
    write_uint16_le,
)


decode_table_1 = b' etainosrlhcdupm'
decode_table_2 = b'tasio wb rnsdalmh ieorasnrtlc synstcloer dtgesionr ufmsw tep.icae oiadur laeiyodeia otruetoakhlr eiu,.oansrctlaileoiratpeaoip bm'


@collect(bytes)
def decode1(text: bytes) -> Iterator[int]:
    for cchar in text:
        if cchar & 0x80:  # first bit as flag
            cchar &= 0x7F
            index = (cchar & 0x78) // 8  # first 4 bits (not MSB) as first char
            yield decode_table_1[index]
            cchar = decode_table_2[cchar]  # 7 bits as second char
        yield cchar


@collect(cast(Callable[[Iterable[bytes]], List[bytes]], list))
def escape_empty_seps(parts: Sequence[bytes]) -> Iterator[bytes]:
    yield parts[0]
    idx = 1
    while idx < len(parts):
        if not parts[idx]:
            yield b'\x1b' + parts[idx + 1]
            idx += 1
        else:
            yield parts[idx]
        idx += 1


def decode2(src: bytes) -> bytes:
    parts = src.split(b'\x1b')
    parts = escape_empty_seps(parts)
    return parts[0] + b''.join(
        [bytes([(part[0] + 0x7F) % 256]) + part[1:] for part in parts[1:]]
    )


@collect(bytes)
def encode2(src: bytes) -> Iterator[int]:
    for b in src:
        print(hex(b), b & 0x80)
        if b & 0x80:
            yield 0x1B
            b -= 0x7F
        yield b


def encode_seq(seq: bytes) -> bytes:
    try:
        print(int(b'0x' + seq[:2], 16))
        return bytes([int(b'0x' + seq[:2], 16)]) + seq[2:]
    except:
        return seq


def encode2_escaped(src: bytes) -> bytes:
    parts = src.split(b'\\x')
    return encode2(parts[0] + b''.join(encode_seq(seq) for seq in parts[1:]))


def decode2_escaped(src: bytes) -> bytes:
    parts = src.split(b'\x1b')
    parts = escape_empty_seps(parts)
    res = parts[0] + b''.join(
        [f'\\x{(part[0] + 0x7F) % 256:02X}'.encode() + part[1:] for part in parts[1:]]
    )
    bck = encode2_escaped(res)
    assert bck == src, (bck, src, res)
    return res


def parse(stream: SupportsRead[bytes]) -> Iterator[bytes]:
    first = read_uint16_le(stream)
    stream.seek(-2, 1)
    offs = [read_uint16_le(stream) for _ in range(first // 2)]
    for off in offs:
        assert stream.tell() == off, (stream.tell(), off)
        yield decode2(decode1(readcstr(stream)))


def compose(
    lines: Iterable[Sequence[str]],
    target: str = 'ccode_patch',
    encoding: str = 'cp862',
) -> None:
    grouped = groupby(lines, key=operator.itemgetter(0))
    for tfname, group in grouped:
        basename = os.path.basename(tfname)
        lines_in_group = [line for _, line in group]

        base = len(lines_in_group) * 2

        text = '\0'.join(
            encode2_escaped(
                line.replace('~~~', '\r').replace('>>>', '\t').encode(encoding)
            ).decode(encoding)
            for line in lines_in_group
        )
        offs = [base] + [m.start() + base + 1 for m in re.finditer('\0', text)]

        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, basename), 'wb') as res:
            res.write(
                b''.join(write_uint16_le(off) for off in offs)
                + text.encode(encoding)
                + b'\0'
            )


def write_parsed(
    filename: str,
    instream: IO[bytes],
    outstream: IO[str],
) -> None:
    for line in parse(instream):
        text = (
            line.decode('cp862')
            .replace('"', '""')
            .replace('\r', '~~~')
            .replace('\t', '>>>')
        )
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
        with open('ccode.tsv', 'w', encoding='utf-8') as out:
            for filename in files:
                with open(filename, 'rb') as stream:
                    write_parsed(filename, stream, out)
