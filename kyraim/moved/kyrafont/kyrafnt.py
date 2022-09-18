#!/usr/bin/env python3

import math
import os
import pathlib
import struct
from typing import NamedTuple

from image import save_image_grid
from kyraim.texts import match_archive_files


def read_le_uint16(f):
    return struct.unpack('<H', f[:2])[0]


def sublist(ls, start, size):
    return ls[start : start + size]


def grouper(it, chunk_size):
    return zip(*([iter(it)] * chunk_size))


def flatten(ls):
    return (item for sublist in ls for item in sublist)

_colorMap = list(range(16))
palette = [(133 * x % 256) for x in range(256)] * 3

def decode_line(bbs):
    return list(flatten((_colorMap[b % 16], _colorMap[b // 16]) for b in bbs))


def convert_char(height, chardata, cheights, cwidth):
    charH1, charH2 = cheights
    charH0 = height - sum(cheights)

    pic = [[_colorMap[0]] * cwidth] * charH1

    pic.append([255] * cwidth)

    read_size = math.ceil(cwidth / 2)
    chunked = grouper(chardata[:read_size * charH2], read_size)
    pic += [decode_line(chunk)[:cwidth] for chunk in chunked]

    pic.append([255] * cwidth)

    pic += [[_colorMap[0]] * cwidth] * charH0
    return pic


class FontHeader(NamedTuple):
    file_size: int
    sig: int
    header_size: int
    bitmap_offset: int
    width_table_start: int
    bitmap_start: int
    height_table_start: int


def decode_font_file(filename, stream):
    path = pathlib.Path(filename)
    stem = path.stem

    header = FontHeader(*struct.unpack('<7H', stream.read(14)))

    print((header.file_size, header.sig, header.header_size))
    if header.sig != 0x0500:
        print("DOSFont: invalid font {}: 0x{:04X}".format(filename, header.sig))
        return
    assert stream.tell() == header.header_size == 14, (stream.tell(), header.header_size)
    _magic = stream.read(3)
    numGlyphs = ord(stream.read(1)) + 1
    height = ord(stream.read(1))
    width = ord(stream.read(1))

    print((width, height, numGlyphs))

    print((header.bitmap_offset, header.width_table_start, header.bitmap_start, header.height_table_start))

    assert stream.tell() == header.bitmap_offset, (stream.tell(), header.bitmap_offset)
    bitmapOffsets = [read_le_uint16(stream.read(2)) for _ in range(numGlyphs)]

    assert stream.tell() == header.width_table_start, (stream.tell(), header.width_table_start)
    widths = list(stream.read(numGlyphs))

    assert stream.tell() == header.bitmap_start, (stream.tell(), header.bitmap_start)
    bitmap_data = stream.read(header.height_table_start - header.bitmap_start)

    assert stream.tell() == header.height_table_start, (stream.tell(), header.height_table_start)
    heights = [tuple(stream.read(2)) for _ in range(numGlyphs)]

    chars = (convert_char(height, bitmap_data[offset - header.bitmap_start:], cheights, cwidth) for offset, cheights, cwidth in zip(bitmapOffsets, heights, widths))

    assert stream.tell() == header.file_size

    save_image_grid(f'{stem}.png', chars, palette)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('directory', help='files to extract')
    args = parser.parse_args()

    for pak, pattern, fname in match_archive_files(
        args.directory, ['*.FNT']
    ):
        bname = os.path.basename(fname)
        print(fname)
        with pak.open(fname, 'rb') as stream:
            decode_font_file(fname, stream)
