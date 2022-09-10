import io

from kyraim.codex.base import BufferLike, read_uint16_le


def decompress_xor_buffer(buffer: BufferLike) -> bytes:
    src = bytes(buffer)

    output = bytearray()
    with io.BytesIO(src) as stream:
        while True:
            code = stream.read(1)[0]
            # print('XOR CODE', code)
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


XOR_SMALL = 127
XOR_MED = 255
XOR_LARGE = 16383
XOR_MAX = 32767


def compress_xor_buffer(
    buffer: BufferLike,
    # orig
) -> bytes:
    size = len(buffer)
    pos = 0
    out = bytearray()
    while pos < size:
        # print(pos, size)
        # assert orig[:len(out)] == out, (list(orig[:len(out)][-20:]), list(out[-20:]))
        fill_count = 0
        xor_count = 0
        skip_count = 0

        last_xor = buffer[pos]
        testsp = pos

        while testsp < size and buffer[testsp] != 0:
            if buffer[testsp] == last_xor:
                fill_count += 1
                xor_count += 1
            else:
                if fill_count > 3:
                    break
                else:
                    last_xor = buffer[testsp]
                    fill_count = 1
                    xor_count += 1
            testsp += 1

        fill_count = fill_count if fill_count > 3 else 0
        xor_count -= fill_count
        while xor_count != 0:
            if xor_count < XOR_MED:
                # print('xor_count.if')
                count = min(xor_count, XOR_SMALL)
                out += bytes([count])
            else:
                # print('xor_count.else')
                count = min(xor_count, XOR_LARGE)
                out += bytes([0x80, count, (count >> 8) | 0x80])

            while count != 0:
                out += bytes([buffer[pos]])
                pos += 1
                count -= 1
                xor_count -= 1

        while fill_count != 0:
            if fill_count <= XOR_MED:
                # print('fill_count.if')
                count = fill_count
                out += bytes([0, count])
            else:
                # print('fill_count.else')
                count = min(fill_count, XOR_LARGE)
                out += bytes([0x80, count % 256, (count >> 8) | 0xC0])

            out += bytes([buffer[pos]])
            pos += count
            fill_count -= count

        while testsp < size and buffer[testsp] == 0:
            skip_count += 1
            testsp += 1

        while skip_count != 0:
            if skip_count < XOR_MED:
                # print('skip_count.if')
                count = min(skip_count, XOR_SMALL)
                out += bytes([count | 0x80])
            else:
                count = min(skip_count, XOR_MAX)
                # print('skip_count.else')
                out += bytes([0x80, count % 256, count >> 8])

            skip_count -= count
            pos += count

    out += bytes([0x80, 0, 0])
    return bytes(out)
