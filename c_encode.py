import glob

from itertools import chain
from functools import partial
import itertools
import operator
import os
import re


def read_uint16_le(stream) -> int:
    return int.from_bytes(stream.read(2), byteorder='little', signed=False)


def readcstr(stream) -> str:
    return b''.join(iter(partial(stream.read, 1), b'\00'))

decode_table_1 = b' etainosrlhcdupm'
decode_table_2 = b'tasio wb rnsdalmh ieorasnrtlc synstcloer dtgesionr ufmsw tep.icae oiadur laeiyodeia otruetoakhlr eiu,.oansrctlaileoiratpeaoip bm'

def decode1(stream):

    text = readcstr(stream)

    out = bytearray()
    for cchar in text:
        if cchar & 0x80:  # first bit as flag
            cchar &= 0x7F
            index = (cchar & 0x78) // 8  # first 4 bits (not MSB) as first char
            out += bytes([decode_table_1[index]])
            cchar = decode_table_2[cchar]  # 7 bits as second char
        out += bytes([cchar])

    return bytes(out)


def decode2(src):
    parts = src.split(b'\x1b')
    return parts[0] + b''.join(
        [bytes([(part[0] + 0x7F) % 256]) + part[1:] for part in parts[1:]]
    )


def encode2(src):
    out = bytearray()
    for b in src:
        print(hex(b), b & 0x80)
        if b & 0x80:
            out += b'\x1b'
            b -= 0x7F
        out += bytes([b])

    return bytes(out)

def encode_seq(seq):
    try:
        print(int(b'0x' + seq[:2], 16))
        return bytes([int(b'0x' + seq[:2], 16)]) + seq[2:]
    except:
        return seq


def encode2_escaped(src):
    parts = src.split(b'\\x')
    src = parts[0] + b''.join(encode_seq(seq) for seq in parts[1:])
    out = bytearray()
    for b in src:
        if b & 0x80:
            out += b'\x1b'
            b -= 0x7F
        out += bytes([b])

    return bytes(out)


def decode2_escaped(src):
    parts = src.split(b'\x1b')
    res = parts[0] + b''.join(
        [f'\\x{(part[0] + 0x7F) % 256:02X}'.encode() + part[1:] for part in parts[1:]]
    )
    bck = encode2_escaped(res)
    assert bck == src, (bck, src, res)
    return res


def parse(fname):
    # print(fname)
    with open(fname, 'rb') as stream:
        first = read_uint16_le(stream)
        stream.seek(-2, 1)
        offs = [read_uint16_le(stream) for _ in range(first // 2)]
        # print(offs)
        for off in offs:
            assert stream.tell() == off, (stream.tell(), off)
            yield decode2_escaped(decode1(stream))


def split_lines(lines):
    for line in lines:
        print(repr(line))
        fname, line = line[:-1].split('\t', maxsplit=1)
        yield fname, line


def write_uint16_le(num) -> int: 
    return num.to_bytes(2, byteorder='little', signed=False)



def compose(fname):
    # print(fname)
    with open(fname, 'r', encoding='windows-1255', errors='ignore') as f:
        grouped = itertools.groupby(split_lines(f), key=operator.itemgetter(0))
        for tfname, group in grouped:
            basename = os.path.basename(tfname)
            lines_in_group = [line for _, line in group]

            base = len(lines_in_group) * 2

            text = '\0'.join(encode2_escaped(line.replace('~~~', '\r').replace('>>>', '\t').encode('cp862')).decode('cp862') for line in lines_in_group)
            offs = [base] + [m.start() + base + 1 for m in re.finditer('\0', text)]

            os.makedirs('ccode_patch', exist_ok=True)
            with open(os.path.join('ccode_patch', basename), 'wb') as res:
                res.write(b''.join(write_uint16_le(off) for off in offs) + text.encode('cp862') + b'\0')
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
