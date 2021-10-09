import numpy as np
from PIL import Image


def read_uint16_le(stream) -> int: 
    return int.from_bytes(stream.read(2), byteorder='little', signed=False)

def read_uint32_le(stream) -> int: 
    return int.from_bytes(stream.read(4), byteorder='little', signed=False)


skip = False


def decode_lcw(f, buffer, size):
    out = list(buffer)
    current = 0
    while True:
        # print(current)
        count = size - current
        if count == 0:
            break

        code = f.read(1)[0]
        print('CODE', code)
        if not (code & 0x80):
            # print('RELATIVE')
            ln = min(count, (code >> 4) + 3)
            offs = ((code & 0xF) << 8) + f.read(1)[0]
            print(f'len = {ln} offs = {offs}')
            dst_offs = current - offs
            # print('DST_OFFS', dst_offs)
            print(len(out), current, offs, dst_offs, out[dst_offs:dst_offs+ln])
            # assert current >= dst_offs + ln, (current, dst_offs)
            # out[current:current+ln] = out[dst_offs:dst_offs+ln]
            for i in range(ln):
                out[current+i] = out[dst_offs+i]
            current += ln
        elif code & 0x40:
            # print('SECOND')
            ln = (code & 0x3F) + 3
            if code == 0xFE:
                ln = read_uint16_le(f)
                if (ln > count):
                    ln = count
                value = f.read(1)[0]
                out[current:current+ln] = [value for _ in range(ln)]
                current += ln
            else:
                # print('ABS')
                if code == 0xFF:
                    ln = read_uint16_le(f)
                offs = read_uint16_le(f)
                if (ln > count):
                    ln = count
                dst_offs = offs
                # assert current >= dst_offs + ln, (current, dst_offs, ln)
                # out[current:current+ln] = out[dst_offs:dst_offs+ln]
                for i in range(ln):
                    out[current+i] = out[dst_offs+i]
                current += ln
        elif code != 0x80:
            ln = min(count, code & 0x3F)
            out[current:current+ln] = list(f.read(ln))
            current += ln
        else:
            break
    return out


if __name__ == '__main__':
    with open('kyra2-cd-ext/OTHER.PAK/PALETTE.COL', 'rb') as f:
        palette = list((x << 2) | (x & 3) for x in f.read(0x300))
    with open('kyra2-cd-ext/MISC_CPS.PAK/_PLAYALL.CPS', 'rb') as f:
    # with open('kyra2-cd-ext/OTHER.PAK/_BUTTONS.CSH', 'rb') as f:
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
            im = decode_lcw(f, [0 for _ in range(width * height)], img_size)
            # f.seek(pos)
            # im = decode_frame(f, im, img_size)
        else:
            raise ValueError(comp)

        assert f.tell() == _file_size + 1, (f.tell(), _file_size)

        # palette = [((53 + x) ** 2 * 13 // 5) % 256 for x in range(256 * 3)] 

        im += [0] * 320 * 200

        # for i in range(10, 321):
        #     bim = np.array(im, dtype=np.uint8)
        #     bim = Image.fromarray(bim[:i*200].reshape(200, i), mode='P')
        #     bim.putpalette(palette)
        #     bim.save(f'palette_{i}.png')


        bim = np.array(im, dtype=np.uint8)
        bim = Image.fromarray(bim[:width*height].reshape(height, width), mode='P')
        bim.putpalette(palette)
        bim.save(f'image.png')
