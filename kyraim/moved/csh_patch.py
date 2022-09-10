import io

import numpy as np
from PIL import Image

from kyraim.codex.base import read_uint16_le, read_uint32_le
from kyraim.codex.lcw import decode_lcw, encode_lcw
from kyraim.cps import read_palette


skip = False


if __name__ == '__main__':
    with open('kyra2-cd-ext/OTHER.PAK/PALETTE.COL', 'rb') as f:
        palette = read_palette(f)
    # with open('kyra2-cd-ext/MISC_CPS.PAK/_PLAYALL.CPS', 'rb') as f:

    # inj = encode_lcw(np.asarray(Image.open('image_csh.png')).ravel()[:-27])
    inj = encode_lcw(bytes(np.asarray(Image.open('image_inj.png')).ravel()[:-27]))
    inj2 = encode_lcw(bytes(np.asarray(Image.open('image_inj2.png')).ravel()[:-27]))
    with open('kyra2-cd-ext/OTHER.PAK/_BUTTONS.CSH', 'rb') as f:
        # with open('orig_1/INTRO1.PAK/TOP.CPS', 'rb') as f:
        if skip:
            print('SKIP', f.read(4))

        width, height = 320, 200

        _file_size = read_uint16_le(f)
        comp = read_uint16_le(f)
        img_size = read_uint32_le(f)
        palen = read_uint16_le(f)
        print(comp, img_size, palen)

        if palen == 0x300:
            palette = read_palette(f)

        if comp == 4:
            pos = f.tell()
            f.seek(0)
            whole = f.read(pos)
            im = decode_lcw(f, b'\0' * img_size, img_size)
            # im = decode_frame(f, im, img_size)
        else:
            raise ValueError(comp)

        assert f.tell() == _file_size + 1, (f.tell(), _file_size)

        patch = bytearray()
        with io.BytesIO(bytes(im)) as csh:
            num_shapes = read_uint16_le(csh)
            offsets_o = [read_uint32_le(csh) for _ in range(num_shapes)]
            print(csh.tell(), offsets_o)

            aft = csh.tell()

            print(csh.read(2))

            offsets = sorted(set(offsets_o) - {0})

            csh.seek(offsets[6] + 8)
            shape_size = read_uint16_le(csh)
            csh.seek(offsets[6])

            csh.seek(offsets[7] + 8)
            shape_size7 = read_uint16_le(csh)
            csh.seek(offsets[7])

            patch += num_shapes.to_bytes(2, signed=False, byteorder='little')
            for off in offsets_o:
                foff = off if off <= offsets[7] else off + len(inj2) + 10 - shape_size7
                print(foff, off)
                patch += foff.to_bytes(4, signed=False, byteorder='little')

            csh.seek(aft)
            origcsh = csh.read()
            patch += origcsh

            origpath = bytes(patch)

            patch[offsets[6] + 8 : offsets[6] + 10] = (10 + len(inj)).to_bytes(
                2, signed=False, byteorder='little'
            )
            patch[offsets[6] + 12 : offsets[6] + 2 + shape_size] = inj + (
                b'\x80' * (shape_size - 10 - len(inj))
            )

            patch[offsets[7] + 8 : offsets[7] + 10] = (10 + len(inj2)).to_bytes(
                2, signed=False, byteorder='little'
            )
            patch[offsets[7] + 12 : offsets[7] + 2 + shape_size7] = inj2 + (
                b'\x80' * (shape_size7 - 10 - len(inj2))
            )

            print('PATCH LEN', len(origpath), len(patch))
            print(bytes(patch)[:50])
            print(bytes(im)[:50])

        encoded = encode_lcw(patch)
        towrite = whole + encoded + b'\x80'
        towrite = (
            (len(towrite) - 1).to_bytes(2, signed=False, byteorder='little')
            + towrite[2:4]
            + (int.from_bytes(towrite[4:8], signed=False, byteorder='little')).to_bytes(
                4, signed=False, byteorder='little'
            )
            + towrite[8:]
        )
        f.seek(0)
        assert whole == f.read(len(whole))
        with open('_buttons.csh', 'wb') as outgg:
            outgg.write(towrite)
