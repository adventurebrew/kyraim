from image_reader import read_image_grid, resize_frame, count_in_row
import numpy as np
import struct

def convert_char(width, frame):
    res = b''
    for line in frame:
        width = len(line)
        pairs = list(zip(*[iter(line)]*2))
        for e, o in pairs:
            res += struct.pack('<B', e + 16 * o)
        if width % 2 == 1:
            res += struct.pack('<B', line[-1] + 16*line[-1]) # check if always zero
    return res


def get_heights(frame):
    line_is_sep = lambda line: line[0] != 255 #all(c == 255 for c in line)
    h1 = count_in_row(line_is_sep, frame)
    h2 = count_in_row(line_is_sep, frame[h1 + 1:])
    return (h1, h2), frame[h1 + 1: h1 + h2 + 1]

frames = list(read_image_grid('chars.png'))
frames = [resize_frame(f) for f in frames]
frames = [ f for f in frames if f != None]
frames = [(l, get_heights(f)) for l, f in frames]

numGlyphs = len(frames)
heights = []
widths = []
bitmaps = b''
bitmapOffsetsStart = 20
widthTableStart = bitmapOffsetsStart + numGlyphs * 2
bitmapsStart = widthTableStart + numGlyphs
bOffsets = [bitmapsStart]


for (w, ((h1, h2), data)) in frames:
    bitmap = convert_char(w, data)
    bOffsets.append(bOffsets[-1] + len(bitmap))
    bitmaps += bitmap
    heights.append(h1)
    heights.append(h2)
    widths.append(w)

heightTableStart = bitmapsStart + len(bitmaps)

size = heightTableStart + 2 * numGlyphs # 0-2
fontSig = 0x0500 # 2-4
descOfset = 14 # 4-6
bitmapOffsetsStart = bitmapOffsetsStart # 6-8
widthTableStart = widthTableStart # 8-10
bitmapsStart = bitmapsStart # 10-12
heightTableStart = heightTableStart # 12-14
something = b'\x11\x10\x00' # 15-17
numGlyphs = numGlyphs # 17
height = 10 # 18
width = 10 # 19
bOffsets = bOffsets[:-1] # 20 - 530
widths = widths # 530 - 785
bitmaps = bitmaps # 785 - ?
heights = heights # ? - END

fileData = struct.pack('<7H',
    size,
    fontSig,
    descOfset,
    bitmapOffsetsStart,
    widthTableStart,
    bitmapsStart,
    heightTableStart
) + something

fileData += struct.pack('<3B', numGlyphs - 1, height, width)
print((len(fileData), bitmapOffsetsStart))
fileData += struct.pack('<{}H'.format(len(bOffsets)), *bOffsets)
print((len(fileData), widthTableStart))
fileData += struct.pack('<{}B'.format(len(widths)), *widths)
print((len(fileData), bitmapsStart))
fileData += bitmaps
print((len(fileData), heightTableStart))
fileData += struct.pack('<{}B'.format(len(heights)), *heights)

with open('8FAT-NEW.FNT', 'wb') as fntFile:
    fntFile.write(fileData)