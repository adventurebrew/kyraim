import io
import numpy as np
from PIL import Image

from cps_read import decode_lcw


def read_uint16_le(stream) -> int: 
    return int.from_bytes(stream.read(2), byteorder='little', signed=False)

def read_uint32_le(stream) -> int: 
    return int.from_bytes(stream.read(4), byteorder='little', signed=False)


skip = False


if __name__ == '__main__':
    with open('kyra2-cd-ext/OTHER.PAK/PALETTE.COL', 'rb') as f:
        palette = list((x << 2) | (x & 3) for x in f.read(0x300))
    # with open('kyra2-cd-ext/MISC_CPS.PAK/_PLAYALL.CPS', 'rb') as f:
    with open('_BUTTONS.CSH', 'rb') as f:
    # with open('_BUTTONS.CSH', 'rb') as f:
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
            palette = list((x << 2) | (x & 3) for x in f.read(0x300))

        if comp == 4:
            pos = f.tell()
            im = decode_lcw(f, [0 for _ in range(img_size)], img_size)
            # f.seek(pos)
            # im = decode_frame(f, im, img_size)
        else:
            raise ValueError(comp)

        assert f.tell() == _file_size + 1, (f.tell(), _file_size)

        with io.BytesIO(bytes(im)) as csh:
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
                    im = decode_lcw(sh, [0 for _ in range(width * height)], frame_size)
                    bim = Image.fromarray(np.asarray(im, dtype=np.uint8).reshape(height, width), mode='P')
                    bim.putpalette(palette)
                    bim.save(f'image_csh2.png')
                    print(width * height - frame_size)
                    print(sh.read())
