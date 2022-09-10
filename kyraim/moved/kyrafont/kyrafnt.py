#!/usr/bin/env python3

import struct
from image import save_image_grid
import math
import sys


def read_le_uint16(f):
    return struct.unpack('<H', f[:2])[0]


def sublist(ls, start, size):
    return ls[start : start + size]


def grouper(it, chunk_size):
    return zip(*([iter(it)] * chunk_size))


filename = sys.argv[1]
if len(sys.argv) < 2:
    exit(1)

with open(filename, 'rb') as fntFile:
    data = fntFile.read()

fileSize, fontSig, descOffset = struct.unpack('<3H', data[0:6])

print((fileSize, fontSig, descOffset))
if fontSig != 0x0500:
    raise ValueError("DOSFont: invalid font: 0x{:04X})".format(fontSig))


width = data[descOffset + 5]
height = data[descOffset + 4]
numGlyphs = data[descOffset + 3] + 1

print((width, height, numGlyphs))

bitmapOffsetsStart, _widthTableStart, unknown2, _heightTableStart = struct.unpack(
    '<4H', data[6:14]
)
print((bitmapOffsetsStart, _widthTableStart, unknown2, _heightTableStart))
bitmapOffsets = [
    read_le_uint16(bytes(t))
    for t in grouper(sublist(data, bitmapOffsetsStart, 2 * numGlyphs), 2)
]
widths = sublist(data, _widthTableStart, numGlyphs)
heights = list(grouper(sublist(data, _heightTableStart, 2 * numGlyphs), 2))

_colorMap = list(range(16))  # [x for x in data[unknow2:unknow2+16]]


def flatten(ls):
    return (item for sublist in ls for item in sublist)


def decode_line(bbs):
    return list(flatten((_colorMap[b % 16], _colorMap[b // 16]) for b in bbs))


def convert_char(c):
    charWidth = widths[c]

    charH1, charH2 = heights[c]
    charH0 = height - sum(heights[c])

    pic = [[_colorMap[0]] * charWidth] * charH1

    pic.append([255] * charWidth)

    read_size = math.ceil(charWidth / 2)
    chunked = grouper(sublist(data, bitmapOffsets[c], read_size * charH2), read_size)
    pic += [decode_line(chunk)[:charWidth] for chunk in chunked]

    pic.append([255] * charWidth)

    pic += [[_colorMap[0]] * charWidth] * charH0
    return pic


chars = (convert_char(c) for c in range(numGlyphs))

locs = [
    {'x1': 0, 'y1': 0, 'x2': widths[c], 'y2': sum(heights[c])} for c in range(numGlyphs)
]

palette = [(133 * x % 256) for x in range(256)] * 3
save_image_grid('chars.png', chars, palette)

# for t, m in heights:
#     print((t, m , height - t - m))

# for i in range(255):
#     # print((i & 1 != 0) == (i % 2 == 1))
#     print(((i & 0xF) % 256) == (i % 16))
