import io
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
            print('RELATIVE')
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
            print('SECOND')
            ln = (code & 0x3F) + 3
            if code == 0xFE:
                ln = read_uint16_le(f)
                if (ln > count):
                    ln = count
                value = f.read(1)[0]
                out[current:current+ln] = [value for _ in range(ln)]
                current += ln
            else:
                print('ABS')
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

UINT16_MAX = (2 ** 16) - 1

def encode_lcw(buffer, orig):

    size = len(buffer)
    pos = 0
    out = bytearray()

    relative = size > UINT16_MAX
    if relative:
        out += bytes([0])

    cmd_onep = len(out)
    out += bytes([0x81, buffer[pos]])
    pos += 1
    cmd_one = True

    while pos < size:
        if size - pos > 64 and buffer[pos] == buffer[pos + 64]:
            rlemax = size if size - pos < UINT16_MAX else pos + UINT16_MAX
            
            rlep = pos + 1
            while rlep < rlemax and buffer[rlep] == buffer[pos]:
                rlep += 1

            run_length = rlep - pos
            assert run_length % UINT16_MAX == run_length

            if run_length >= 0x41:
                cmd_one = False
                out += bytes([0xFE, run_length & 0xFF, (run_length >> 8) & 0xFF, buffer[pos]])
                pos = rlep
                continue

        block_size = 0
        if relative:
            offstart = 0 if pos < UINT16_MAX else pos - UINT16_MAX
        else:
            offstart = 0
        
        offchk = offstart
        offsetp = pos
        while offchk < pos:
            while offchk < pos and buffer[offchk] != buffer[pos]:
                offchk += 1

            if offchk >= pos:
                break

            i = 1
            while pos + i < size:
                if buffer[offchk + i] != buffer[pos + i]:
                    break
                i += 1

            if i >= block_size:
                block_size = i
                offsetp = offchk

            offchk += 1

        if block_size <= 2:
            if cmd_one and out[cmd_onep] < 0xBF:
                out[cmd_onep] += 1
                out += bytes([buffer[pos]])
                pos += 1
            else:
                cmd_onep = len(out)
                out += bytes([0x81, buffer[pos]])
                pos += 1
                cmd_one = True

        else:
            rel_offset = pos - offsetp
            if block_size > 0xA or rel_offset > 0xFFF:
                if block_size > 0x40:
                    out += bytes([0xFF, block_size & 0xFF, (block_size >> 8) & 0xFF])
                else:
                    out += bytes([(block_size - 3) | 0xC0])

                offset = rel_offset if relative else offsetp
            else:
                offset = ((rel_offset << 8) % UINT16_MAX) | ((16 * (block_size - 3) + (rel_offset // 256)) % UINT16_MAX)

            out += bytes([offset % 256, offset // 256])
            pos += block_size
            cmd_one = False

        # if orig[:len(out)] !=  bytes(out):
        #     print(orig[:len(out)])
        #     print(bytes(out))
        #     exit(1)

    # out += bytes([0x80])
    return bytes(out)


if __name__ == '__main__':
    with open('kyra2-cd-ext/OTHER.PAK/PALETTE.COL', 'rb') as f:
    # with open('orig_1/INTRO1.PAK/TOP.CPS', 'rb') as f:
    #     f.seek(10, 0)
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
            im = decode_lcw(f, [0 for _ in range(img_size)], img_size)

            pos2 = f.tell()
            f.seek(pos)
            orig = f.read(pos2 - pos)
            f.seek(pos2)
            comp = encode_lcw(im, orig)

            # # HARD COMPARISON
            # assert comp == orig

            # SOFT COMPARISON
            with io.BytesIO(comp) as ins:
                print('====================')
                uncomp = decode_lcw(ins, [0 for _ in range(img_size)], img_size)
                assert im == uncomp, (im, uncomp)
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
