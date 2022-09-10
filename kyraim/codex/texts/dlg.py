import csv
import glob

import operator
import os
from itertools import chain, groupby
from typing import IO, Iterable, Iterator, Sequence, Tuple

from kyraim.codex.base import SupportsRead, read_uint16_le, write_uint16_le


def parse(stream: SupportsRead[bytes]) -> Iterator[Tuple[int, int, int, bytes]]:
    stream.seek(0, 2)
    fsize = stream.tell()
    stream.seek(0, 0)

    cs_entry = read_uint16_le(stream)
    voc_h = read_uint16_le(stream)
    sc_index1 = read_uint16_le(stream)
    sc_index2 = read_uint16_le(stream)

    # print(f'cs_entry={cs_entry}, voc_h={voc_h}, sc_index1={sc_index1}, sc_index2={sc_index2}')

    first_off = read_uint16_le(stream)
    num_entries = (first_off - stream.tell()) // 2
    offs = [first_off] + [read_uint16_le(stream) for _ in range(num_entries)]

    assert stream.tell() == offs[0], (stream.tell(), offs[0])

    print(offs)

    for off in offs[:-1]:
        assert stream.tell() == off, (stream.tell(), off)
        # print(f'START OFFSET {off}')
        while True:
            cmd = read_uint16_le(stream)
            if cmd == 4:
                cs_entry = read_uint16_le(stream)
                yield (
                    off,
                    cmd,
                    cs_entry,
                    b'',
                )
                continue
            elif cmd == 10:
                unk = read_uint16_le(stream)
                # print('BREAK 10', unk)
                yield (
                    off,
                    cmd,
                    unk,
                    b'',
                )
                break
            else:
                len = read_uint16_le(stream)
                voc_lo = read_uint16_le(stream)
                # stream.read(len).decode('cp862')
                yield (
                    off,
                    cmd,
                    voc_lo,
                    stream.read(len),
                )
    assert stream.read() == b''


def generate_dialogues(lines, encoding):
    out = bytearray()
    for line in lines:
        text = ''
        off, cmd, param = line.split('\t', maxsplit=2)
        print(line)
        cmd = int(cmd)
        if int(cmd) in {4, 10}:
            param = int(param)
            out += write_uint16_le(cmd)
            if param != 0:
                out += write_uint16_le(param)
            if cmd == 10:
                print('yield', off, bytes(out))
                yield bytes(out)
                out = bytearray()
        else:
            voc_lo, text = param.split('\t', maxsplit=1)
            voc_lo = int(voc_lo)
            out += (
                write_uint16_le(cmd)
                + write_uint16_le(len(text))
                + write_uint16_le(voc_lo)
                + text.encode(encoding)
            )


def compose(
    lines: Iterable[Sequence[str]],
    target: str = 'dlg_patch',
    encoding: str = 'windows-1255',
) -> None:
    # print(fname)
    grouped = groupby(lines, key=operator.itemgetter(0))
    for tfname, group in grouped:
        basename = os.path.basename(tfname)
        lines_in_group = ['\t'.join(line) for _, *line in group]
        outs = list(generate_dialogues(lines_in_group, encoding))
        num_entries = len(outs)
        first_off = 8 + (num_entries + 1) * 2

        offs = bytearray()
        for entry in outs:
            offs += write_uint16_le(first_off)
            first_off += len(entry)
        offs += write_uint16_le(5)

        with open(os.path.join('orig', tfname), 'rb') as src:
            header = src.read(8)

        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, basename), 'wb') as res:
            res.write(header + bytes(offs) + b''.join(outs))


def write_parsed(
    filename: str,
    instream: IO[bytes],
    outstream: IO[str],
) -> None:
    for (off, cmd, voc_lo, line) in parse(instream):
        text = line.decode('windows-1255').replace('"', '""')
        assert '\n' not in text
        print(
            os.path.basename(filename),
            off,
            cmd,
            voc_lo,
            f'"{text}"',
            sep='\t',
            file=outstream,
        )


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
        with open('dlg.tsv', 'w', encoding='utf-8') as out:
            for filename in files:
                with open(filename, 'rb') as stream:
                    write_parsed(filename, stream, out)
