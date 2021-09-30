import glob
import os
import itertools
import operator

from chunk import Chunk
from itertools import chain, takewhile
from functools import partial

def read_uint16_le(stream) -> int: 
    return int.from_bytes(stream.read(2), byteorder='little', signed=False)


def write_uint16_le(num) -> int: 
    return num.to_bytes(2, byteorder='little', signed=False)


def read_chunks(stream, **kwargs):
    while True:
        try:
            chunk = Chunk(stream, **kwargs)
        except EOFError:
            break
        yield chunk
        chunk.skip()

def before_offset(stream, off, *args) -> bool:
    return stream.tell() <= off

def readcstr(stream) -> str:
    return b''.join(iter(partial(stream.read, 1), b'\00')).decode('cp862')

def split_lines(lines):
    for line in lines:
        fname, line = line[:-1].split('\t', maxsplit=1)
        yield fname, line


def generate_dialogues(lines):
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
            vocLo, text = param.split('\t', maxsplit=1)
            vocLo = int(vocLo)
            out += write_uint16_le(cmd) + write_uint16_le(len(text)) + write_uint16_le(vocLo) + text.encode('windows-1255')


def compose(fname):
    # print(fname)
    with open(fname, 'r', encoding='windows-1255') as f:
        grouped = itertools.groupby(split_lines(f), key=operator.itemgetter(0))
        for tfname, group in grouped:
            basename = os.path.basename(tfname)
            lines_in_group = [line for _, line in group]
            outs = list(generate_dialogues(lines_in_group))
            num_entries = len(outs)
            first_off = 8 + (num_entries + 1) * 2

            offs = bytearray()
            for entry in outs:
                offs += write_uint16_le(first_off)
                first_off += len(entry)
            offs += write_uint16_le(5)

            with open(tfname, 'rb') as src:
                header = src.read(8) 

            os.makedirs('dlg_patch', exist_ok=True)
            with open(os.path.join('dlg_patch', basename), 'wb') as res:
                res.write(header + bytes(offs) + b''.join(outs))
                # if not res.tell() % 2:
                #     res.write(b'\x00\x00')


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('files', nargs='+', help='files to extract')
    args = parser.parse_args()

    files = sorted(set(chain.from_iterable(glob.iglob(r) for r in args.files)))
    print(files)
    for filename in files:
        compose(filename)
