import io
import os
import pathlib
from typing import Iterable, cast

import numpy as np
from PIL import Image

from kyraim.codex.lcw import decode_lcw, encode_lcw
from kyraim.codex.xor_delta import compress_xor_buffer, decompress_xor_buffer


if __name__ == '__main__':

    dir = pathlib.Path('title2/thisone')
    files = os.listdir(dir)

    num_frames = len(files)
    xpos, ypos = 0, 0

    first_frame_im = Image.open(dir / files[0])
    width, height = first_frame_im.size
    lcw_buffer_size = 11838
    flags = 1

    palette = bytes(x >> 2 for x in cast(Iterable[int], first_frame_im.getpalette()))
    first_frame = np.asarray(first_frame_im, dtype=np.uint8).ravel()
    encoded_xor = compress_xor_buffer(bytes(first_frame))
    assert lcw_buffer_size - len(encoded_xor) > 0
    encoded_xor += b'\0' * (lcw_buffer_size - len(encoded_xor))
    print(len(encoded_xor))
    off = 126
    offs = [off]
    encoded_lcw = encode_lcw(encoded_xor)
    output = bytearray(encoded_lcw)
    for f in files[1:]:
        off += len(encoded_lcw)
        offs += [off]
        frame = np.asarray(Image.open(dir / f), dtype=np.uint8).ravel()
        encoded_xor = compress_xor_buffer(bytes(frame ^ first_frame))
        assert decompress_xor_buffer(encoded_xor) == bytes(frame ^ first_frame)
        assert lcw_buffer_size - len(encoded_xor) > 0
        encoded_xor += b'\0' * (lcw_buffer_size - len(encoded_xor))
        first_frame = frame
        encoded_lcw = encode_lcw(encoded_xor)
        with io.BytesIO(encoded_lcw) as fd:
            dec = decode_lcw(fd, b'\0' * lcw_buffer_size, lcw_buffer_size)
            assert bytes(dec) == encoded_xor, (bytes(dec)[:50], encoded_xor[:50])
        output += encoded_lcw

    off += len(encoded_lcw)
    offs += [off]

    with open('TITLE.WSA', 'wb') as outfile:
        outfile.write(
            num_frames.to_bytes(2, signed=False, byteorder='little')
            + xpos.to_bytes(2, signed=False, byteorder='little')
            + ypos.to_bytes(2, signed=False, byteorder='little')
            + width.to_bytes(2, signed=False, byteorder='little')
            + height.to_bytes(2, signed=False, byteorder='little')
            + lcw_buffer_size.to_bytes(2, signed=False, byteorder='little')
            + flags.to_bytes(2, signed=False, byteorder='little')
            + b''.join(
                off.to_bytes(4, signed=False, byteorder='little') for off in offs
            )
            + (0).to_bytes(4, signed=False, byteorder='little')
        )
        print(outfile.tell())
        outfile.write(palette + output)
