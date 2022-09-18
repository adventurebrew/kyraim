#!/usr/bin/env python3

import math
import os
import pathlib
import struct
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


def decode_font_file(filename, data):
    path = pathlib.Path(filename)
    stem = path.stem

    fileSize, fontSig, descOffset = struct.unpack('<3H', data[0:6])

    print((fileSize, fontSig, descOffset))
    if fontSig != 0x0500:
        print("DOSFont: invalid font {}: 0x{:04X}".format(filename, fontSig))
        return

    assert len(data) == fileSize
    assert descOffset == 14, descOffset
    bitmapOffsetsStart, _widthTableStart, unknown2, _heightTableStart = struct.unpack(
        '<4H', data[6:14]
    )
    print(data[descOffset:descOffset+2])
    numGlyphs = data[descOffset + 3] + 1
    height = data[descOffset + 4]
    width = data[descOffset + 5]

    print((width, height, numGlyphs))

    print((bitmapOffsetsStart, _widthTableStart, unknown2, _heightTableStart))
    bitmapOffsets = [
        read_le_uint16(bytes(t))
        for t in grouper(sublist(data, bitmapOffsetsStart, 2 * numGlyphs), 2)
    ]
    widths = sublist(data, _widthTableStart, numGlyphs)
    heights = list(grouper(sublist(data, _heightTableStart, 2 * numGlyphs), 2))

    assert len(bitmapOffsets) == len(widths) == len(heights) == numGlyphs, (len(bitmapOffsets), len(widths), len(heights), numGlyphs)

    chars = (convert_char(height, data[offset:], cheights, cwidth) for offset, cheights, cwidth in zip(bitmapOffsets, heights, widths))

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
            data = stream.read()

        decode_font_file(fname, data)
