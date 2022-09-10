import io

import numpy as np
from PIL import Image

from kyraim.codex.base import read_uint16_le, read_uint32_le
from kyraim.codex.lcw import decode_lcw
from kyraim.cps import decode_cps, read_palette


skip = False


if __name__ == '__main__':
    with open('../kyraim/kyra2-cd-ext/OTHER.PAK/PALETTE.COL', 'rb') as f:
        palette = read_palette(f)
    with open('../kyraim/kyra2-cd-ext/OTHER.PAK/_BUTTONS.CSH', 'rb') as f:
        xim, _ = decode_cps(f, palette, decode=False)

        with io.BytesIO(xim) as csh:
            num_shapes = read_uint16_le(csh)
            offsets = [read_uint32_le(csh) for _ in range(num_shapes)]
            print(csh.tell(), offsets)

            print(csh.read(2))

            offsets = sorted(set(offsets) - {0})

            csh.seek(offsets[7])
            for off in offsets[7:8]:
                assert csh.tell() == off, (csh.tell(), off)
                print(csh.read(2))
                flags = read_uint16_le(csh)
                height = csh.read(1)[0]
                width = read_uint16_le(csh)
                unk = csh.read(1)[0]
                shape_size = read_uint16_le(csh)
                print(flags, height, width, unk, shape_size)
                frame_size = read_uint16_le(csh)

                print(frame_size, width, height, width * height)
                print(frame_size, shape_size)

                shape = csh.read(shape_size - 10)
                assert not flags & 2
                with io.BytesIO(shape) as sh:
                    im = decode_lcw(sh, b'\0' * width * height, frame_size)
                    bim = Image.fromarray(
                        np.frombuffer(im, dtype=np.uint8).reshape(height, width),
                        mode='P',
                    )
                    bim.putpalette(palette)
                    bim.save(f'image_csh2.png')
                    print(width * height - frame_size)
                    print(sh.read())
