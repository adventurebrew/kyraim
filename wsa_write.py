import io
import os
import pathlib

import numpy as np
from PIL import Image

from cps_read import decode_lcw, encode_lcw, read_uint16_le, read_uint32_le
from wsa_read import decompress_xor_buffer, compress_xor_buffer

if __name__ == '__main__':

    dir = pathlib.Path('title2/thisone')
    files = os.listdir(dir)
    
    num_frames = len(files)
    xpos, ypos = 0, 0

    first_frame = Image.open(dir / files[0])
    width, height = first_frame.size
    lcw_buffer_size = 11838
    flags = 1

    palette = bytes(x >> 2 for x in first_frame.getpalette())
    first_frame = np.asarray(first_frame, dtype=np.uint8).ravel()
    encoded_xor = compress_xor_buffer(first_frame)
    assert lcw_buffer_size - len(encoded_xor) > 0
    encoded_xor += b'\0' * (lcw_buffer_size - len(encoded_xor))
    print(len(encoded_xor))
    off = 126
    offs = [off]
    encoded_lcw = encode_lcw(encoded_xor, None)[:-1]
    output = bytearray(encoded_lcw)
    for f in files[1:]:
        off += len(encoded_lcw)
        offs += [off]
        frame = np.asarray(Image.open(dir / f), dtype=np.uint8).ravel()
        encoded_xor = compress_xor_buffer(np.asarray(frame ^ first_frame, dtype=np.uint8))
        assert decompress_xor_buffer(encoded_xor) == bytes(frame ^ first_frame)
        assert lcw_buffer_size - len(encoded_xor) > 0
        encoded_xor += b'\0' * (lcw_buffer_size - len(encoded_xor))
        first_frame = frame
        encoded_lcw = encode_lcw(encoded_xor, None)[:-1]
        with io.BytesIO(encoded_lcw) as fd:
            dec = decode_lcw(fd, [0 for _ in range(lcw_buffer_size)], lcw_buffer_size)
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
            + b''.join(off.to_bytes(4, signed=False, byteorder='little') for off in offs)
            + (0).to_bytes(4, signed=False, byteorder='little')
        )
        print(outfile.tell())
        outfile.write(
            palette
            + output
        )
