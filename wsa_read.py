import io

import numpy as np
from PIL import Image

from cps_read import decode_lcw, read_uint16_le, read_uint32_le


WSA_FLAGS = {
    'WF_OFFSCREEN_DECODE': 0x10,
    'WF_NO_LAST_FRAME': 0x20,
    'WF_NO_FIRST_FRAME': 0x40,
    'WF_FLIPPED': 0x80,
    'WF_HAS_PALETTE': 0x100,
    'WF_XOR': 0x200
}


def decompress_xor_buffer(buffer):
    src = bytes(buffer)

    output = bytearray()
    print(src)
    with io.BytesIO(src) as stream:
        while True:
            code = stream.read(1)[0]
            print('XOR CODE', code)
            if code == 0:
                ln = stream.read(1)[0]
                output += stream.read(1) * ln

            elif code & 0x80:
                code -= 0x80
                if code != 0:
                    output += b'\x00' * code
                else:
                    subcode = read_uint16_le(stream)
                    if subcode == 0:
                        break
                    elif subcode & 0x8000:
                        subcode -= 0x8000
                        if subcode & 0x4000:
                            ln = subcode - 0x4000
                            output += stream.read(1) * ln
                        else:
                            output += stream.read(code)
                    else:
                        output += b'\x00' * subcode
            else:
                output += stream.read(code)

        return bytes(output)


if __name__ == '__main__':

    with open('orig_1/INTRO1.PAK/TOP.CPS', 'rb') as f:
        f.seek(10, 0)
        _palette = list((x << 2) | (x & 3) for x in f.read(0x300))

    with open('orig_1/INTRO1.PAK/KYRANDIA.WSA', 'rb') as f:

        # https://moddingwiki.shikadi.net/wiki/Westwood_WSA_Format
        # UINT16LE	NrOfFrames	Number of frames.
        # UINT16LE	XPos	X-offset of the frame data. This field does not appear in the Dune II versions of the format.
        # UINT16LE	YPos	Y-offset of the frame data. This field does not appear in the Dune II versions of the format.
        # UINT16LE	Width	Width of the frames.
        # UINT16LE	Height	Height of the frames.
        # UINT16LE	DeltaBufferSize	Size of the buffer required to unpack the frame data. Through some development quirk, this value is always 37 bytes smaller than the actual required buffer size. This field is a UINT32LE in the Monopoly version of the format.
        # UINT16LE	Flags	Extra load options. The only available option is HasPalette, which is bit 1. This field does not appear in the Dune II v1.00 version of the format, meaning that version can never have an embedded palette.
        # UINT32LE[NrOfFrames+2]	FrameOffsets	Addresses of the frame offsets. The addresses are relative to the start of the file, but do not take the palette into account, meaning that if the HasPalette flag is enabled, 768 bytes need to be added to these offsets to find the actual data.
        # BYTE[768]	Palette	A 256-colour 6-bit RGB VGA palette. Only occurs if the HasPalette flag is enabled. This is an 8-bit RGB VGA palette in the Monopoly version of the format.

        num_frames = read_uint16_le(f)
        # xpos = read_uint16_le(f)
        # ypos = read_uint16_le(f)
        width = read_uint16_le(f)
        height = read_uint16_le(f)
        lcw_buffer_size = read_uint16_le(f)
        flags = read_uint16_le(f)
        offs = [read_uint32_le(f) for _ in range(num_frames + 1)]
        file_size = read_uint32_le(f)
        # palette = f.read(3 * 256)

        print(num_frames, width, height, lcw_buffer_size)

        frame = np.zeros((height, width), dtype=np.uint8)
        lcw_buffer = [0 for _ in range(lcw_buffer_size)]

        for idx, off in enumerate(offs):
            assert f.tell() == off, (f.tell(), off)
            lcw_buffer = decode_lcw(f, lcw_buffer, lcw_buffer_size)

            decoded_xor = np.frombuffer(decompress_xor_buffer(lcw_buffer), dtype=np.uint8).reshape(height, width)
            frame ^= decoded_xor
            im = Image.fromarray(frame.reshape(height, width), mode='P')
            im.putpalette(_palette)
            print(_palette)
            im.save(f'frame_{idx:05d}.png')

        assert f.read() == b''
        assert f.tell() == file_size, (f.tell(), file_size)
