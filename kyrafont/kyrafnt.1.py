#!/usr/bin/env python3

import struct
from image import save_image_grid
from math import ceil

with open('8FAT.FNT', 'rb') as fntFile:
    data = fntFile.read()

fileSize, fontSig, descOffset = struct.unpack('<3H', data[0:6])

print((fileSize, fontSig, descOffset))
if (fontSig != 0x0500):
    raise ValueError("DOSFont: invalid font: 0x{:04X})".format(fontSig))

width = data[descOffset + 5]
height = data[descOffset + 4]
numGlyphs = data[descOffset + 3] + 1

print((width, height, numGlyphs))

bitmapOffsetsStart, _widthTableStart, unknown2, _heightTableStart = struct.unpack('<4H', data[6:14])
print((bitmapOffsetsStart, _widthTableStart, unknown2, _heightTableStart))
bitmapOffsets = data[bitmapOffsetsStart:]
bitmapOffsets = [struct.unpack('<H', bitmapOffsets[2*i:2*i + 2])[0] for i in range(numGlyphs)]
widths = [x for x in data[_widthTableStart:_widthTableStart + numGlyphs]]
heights = [x for x in data[_heightTableStart:_heightTableStart + 2 * numGlyphs]]
heights = list(zip(*[iter(heights)]*2))
_colorMap = list(range(16)) # [x for x in data[unknow2:unknow2+16]]
_colorMap[1] = 128
_colorMap[3] = 64

def convert_char(c):
    src = data[bitmapOffsets[c]:]
    charWidth = widths[c]
    
    charH1, charH2 = heights[c]
    charH0 = height - (charH1 + charH2)

    print((bitmapOffsets[c] + (ceil(charWidth / 2) * charH2) - 1, bitmapOffsets[c + 1]))

    soff = 0

    # pic = []
    # for _ in range(charH1):
    #     pp = [_colorMap[0]] * charWidth
    #     # pp = [0] * charWidth
    #     # col = _colorMap[0]
    #     # for i in range(charWidth):
    #     #     if col != 0:
    #     #         pp[i] = col
    #     pic.append(pp)
    pic = [[_colorMap[0]] * charWidth] * charH1

    pic.append([255] * charWidth)
    for _ in range(charH2):
        b = 0
        pp = [0] * charWidth
        for i in range(charWidth):
            if (i % 2 == 0): # was i & 1
                b = src[soff]
                soff += 1
                col = _colorMap[b % 16] # was _colorMap[(b & 0xF) % 256]
            else:
                col = _colorMap[int(b / 16)]
            # if col != 0:
            #     pp[i] = col
            pp[i] = col
        pic.append(pp)

    pic.append([255] * charWidth)

    # for _ in range(charH0):
    #     pic += [_colorMap[0]] * charWidth
    #     # pp = [0] * charWidth
    #     # col = _colorMap[0]
    #     # for i in range(charWidth):
    #     #     if col != 0:
    #     #         pp[i] = col
    #     pic.append(pp)

    pic += [[_colorMap[0]] * charWidth] * charH0
    return pic

chars = (convert_char(c) for c in range(numGlyphs))
pallete = range(3*255)
pallete = (x % 256 for x in pallete)
pallete = list(zip(*[iter(pallete)]*3))

locs = [{'x1': 0, 'y1': 0, 'x2': widths[c], 'y2': sum(heights[c])} for c in range(numGlyphs)]
save_image_grid('chars.png', chars)

# for t, m in heights:
#     print((t, m , height - t - m))

# for i in range(255):
#     # print((i & 1 != 0) == (i % 2 == 1))
#     print(((i & 0xF) % 256) == (i % 16))
    