from typing import IO

from kyraim.codex.base import BufferLike, read_uint16_le


def decode_lcw(stream: IO[bytes], buffer: BufferLike, size: int) -> bytes:
    out = bytearray(buffer)
    current = 0
    while True:
        # print(current)
        count = size - current

        if count == 0:
            # TODO: check if can be removed (side effect of trailing byte 0x80)
            break

        code = stream.read(1)[0]
        if code == 0x80:
            break

        # print('CODE', code)
        if not (code & 0x80):
            # print('RELATIVE')
            ln = min(count, (code >> 4) + 3)
            offs = ((code & 0xF) << 8) + stream.read(1)[0]
            # print(f'len = {ln} offs = {offs}')
            dst_offs = current - offs
            # print('DST_OFFS', dst_offs)
            # print(len(out), current, offs, dst_offs, out[dst_offs : dst_offs + ln])
            # assert current >= dst_offs + ln, (current, dst_offs)
            # out[current:current+ln] = out[dst_offs:dst_offs+ln]
            for i in range(ln):
                out[current + i] = out[dst_offs + i]
            current += ln
        elif code & 0x40:
            # print('SECOND')
            ln = min(count, (code & 0x3F) + 3)
            if code == 0xFE:
                ln = min(count, read_uint16_le(stream))
                out[current : current + ln] = stream.read(1) * ln
                current += ln
            else:
                # print('ABS')
                if code == 0xFF:
                    ln = min(count, read_uint16_le(stream))
                offs = read_uint16_le(stream)
                dst_offs = offs
                # assert current >= dst_offs + ln, (current, dst_offs, ln)
                # out[current:current+ln] = out[dst_offs:dst_offs+ln]
                for i in range(ln):
                    out[current + i] = out[dst_offs + i]
                current += ln
        else:
            assert code != 0x80
            ln = min(count, code & 0x3F)
            out[current : current + ln] = stream.read(ln)
            current += ln
    return bytes(out)


UINT16_MAX = (2**16) - 1


def encode_lcw(buffer: BufferLike) -> bytes:

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
                out += bytes(
                    [0xFE, run_length & 0xFF, (run_length >> 8) & 0xFF, buffer[pos]]
                )
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
                offset = ((rel_offset << 8) % UINT16_MAX) | (
                    (16 * (block_size - 3) + (rel_offset // 256)) % UINT16_MAX
                )

            out += bytes([offset % 256, offset // 256])
            pos += block_size
            cmd_one = False

    return bytes(out)
    # return bytes(out) + b'\x80'
