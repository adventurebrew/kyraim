import glob
import os
from pathlib import Path

import numpy as np
from PIL import Image

from kyraim.codex.base import read_uint16_le, read_uint32_le
from kyraim.codex.lcw import decode_lcw
from kyraim.codex.xor_delta import compress_xor_buffer, decompress_xor_buffer
from kyraim.cps import decode_cps, read_palette


WSA_FLAGS = {
    'WF_OFFSCREEN_DECODE': 0x10,
    'WF_NO_LAST_FRAME': 0x20,
    'WF_NO_FIRST_FRAME': 0x40,
    'WF_FLIPPED': 0x80,
    'WF_HAS_PALETTE': 0x100,
    'WF_XOR': 0x200,
}


def decode_wsa_sequence(stream, palette, version='kyra'):

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

    num_frames = read_uint16_le(stream)

    if version == 'kyra2':
        xpos = read_uint16_le(stream)
        ypos = read_uint16_le(stream)

    width = read_uint16_le(stream)
    height = read_uint16_le(stream)
    lcw_buffer_size = read_uint16_le(stream)
    flags = read_uint16_le(stream)
    offs = [read_uint32_le(stream) for _ in range(num_frames + 1)]
    file_size = read_uint32_le(stream)

    has_palette = flags & 1

    if has_palette:
        palette = read_palette(stream)

    print(num_frames, width, height, lcw_buffer_size, flags)
    # print(xpos, ypos)
    print(offs)

    frame = np.zeros((height, width), dtype=np.uint8)
    lcw_buffer = b'\0' * lcw_buffer_size

    for off in offs:
        assert stream.tell() == off + has_palette * len(palette), (
            stream.tell(),
            off + has_palette * len(palette),
        )
        lcw_buffer = b'\0' * lcw_buffer_size

        if off == offs[-1] and file_size == 0:  # kyra2
            break
        lcw_buffer = decode_lcw(stream, lcw_buffer, lcw_buffer_size)

        old_frame = np.array(frame, dtype=np.uint8)  # for verification

        uncomp = decompress_xor_buffer(lcw_buffer)
        comp = compress_xor_buffer(
            uncomp,
            # bytes(lcw_buffer)
        )
        assert decompress_xor_buffer(comp) == uncomp
        # assert comp == bytes(lcw_buffer), (comp, bytes(lcw_buffer))

        decoded_xor = np.frombuffer(
            decompress_xor_buffer(lcw_buffer), dtype=np.uint8
        ).reshape(height, width)
        frame ^= decoded_xor

        assert np.array_equal(decoded_xor, frame ^ old_frame)
        im = Image.fromarray(frame.reshape(height, width), mode='P')
        im.putpalette(palette)
        yield im

    assert stream.read() == b''
    if file_size != 0:
        assert stream.tell() == file_size, (stream.tell(), file_size)


if __name__ == '__main__':

    with open('../kyraim/orig_1/INTRO1.PAK/TOP.CPS', 'rb') as f:
        _, palette = decode_cps(f, None, decode=False)

    frames_dir = Path('frames')

    wsas = sorted(set(glob.iglob('../kyraim/orig_1/*.PAK/KYRANDIA.WSA')))
    for fname in wsas:
        bname = os.path.basename(fname)
        os.makedirs(frames_dir / bname, exist_ok=True)
        with open(fname, 'rb') as fstream:
            print(fname)
            for idx, im in enumerate(
                decode_wsa_sequence(fstream, palette, version='kyra')
            ):
                im.save(frames_dir / bname / f'frame_{idx:05d}.png')

    wsas = sorted(set(glob.iglob('../kyraim/kyra2-cd-ext/*.PAK/TITLE.WSA')))
    for fname in wsas:
        bname = os.path.basename(fname)
        os.makedirs(frames_dir / bname, exist_ok=True)
        with open(fname, 'rb') as fstream:
            print(fname)
            for idx, im in enumerate(
                decode_wsa_sequence(fstream, palette, version='kyra2')
            ):
                im.save(frames_dir / bname / f'frame_{idx:05d}.png')
