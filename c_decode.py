import glob

from itertools import chain
from functools import partial
import os


def read_uint16_le(stream) -> int:
    return int.from_bytes(stream.read(2), byteorder='little', signed=False)


def readcstr(stream) -> str:
    return b''.join(iter(partial(stream.read, 1), b'\00'))


def decode1(stream):
    decode_table_1 = b' etainosrlhcdupm'
    decode_table_2 = b'tasio wb rnsdalmh ieorasnrtlc synstcloer dtgesionr ufmsw tep.icae oiadur laeiyodeia otruetoakhlr eiu,.oansrctlaileoiratpeaoip bm'

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


def decode2_escaped(src):
    parts = src.split(b'\x1b')
    return parts[0] + b''.join(
        [f'\\x{(part[0] + 0x7F) % 256:02X}'.encode() + part[1:] for part in parts[1:]]
    )


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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('files', nargs='+', help='files to extract')
    args = parser.parse_args()

    files = sorted(set(chain.from_iterable(glob.iglob(r) for r in args.files)))
    print(files)
    for filename in files:
        for line in parse(filename):
            text = line.decode('ascii').replace('"', '`')
            assert '\n' not in text
            print(os.path.basename(filename), f'"{text}"', sep='\t')
