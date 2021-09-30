import glob

from chunk import Chunk
from itertools import chain, takewhile
from functools import partial

def read_uint16_le(stream) -> int: 
    return int.from_bytes(stream.read(2), byteorder='little', signed=False)

def read_chunks(stream, **kwargs):
    while True:
        try:
            chunk = Chunk(stream, **kwargs)
        except EOFError:
            break
        yield chunk
        chunk.skip()

def before_offset(stream, off, *args) -> bool:
    return stream.tell() <= off

def readcstr(stream) -> str:
    return b''.join(iter(partial(stream.read, 1), b'\00')).decode('cp862')

def parse(fname):
    # print(fname)
    with open(fname, 'rb') as stream:

        stream.seek(0, 2)
        fsize = stream.tell()
        stream.seek(0, 0)

        csEntry = read_uint16_le(stream)
        vocH = read_uint16_le(stream)
        scIndex1 = read_uint16_le(stream)
        scIndex2 = read_uint16_le(stream)

        # print(f'csEntry={csEntry}, vocH={vocH}, scIndex1={scIndex1}, scIndex2={scIndex2}')

        first_off = read_uint16_le(stream)
        num_entries = (first_off - stream.tell()) // 2
        offs = [first_off] + [read_uint16_le(stream) for _ in range(num_entries)]

        assert stream.tell() == offs[0], (stream.tell(), offs[0])

        print(offs)

        for off in offs[:-1]:
            assert stream.tell() == off, (stream.tell(), off)
            # print(f'START OFFSET {off}')
            while True:
                cmd = read_uint16_le(stream)
                if cmd == 4:
                    csEntry = read_uint16_le(stream)
                    print(fname, off, cmd, csEntry, sep='\t')
                    continue
                elif cmd == 10:
                    unk = read_uint16_le(stream)
                    # print('BREAK 10', unk)
                    print(fname, off, cmd, unk, sep='\t')
                    break
                else:
                    len = read_uint16_le(stream)
                    vocLo = read_uint16_le(stream)
                    # stream.read(len).decode('cp862')
                    print(
                        fname,
                        off,
                        cmd,
                        vocLo,
                        stream.read(len).decode('cp862'),
                        sep='\t',
                    )
        assert stream.read() == b''


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('files', nargs='+', help='files to extract')
    args = parser.parse_args()

    files = sorted(set(chain.from_iterable(glob.iglob(r) for r in args.files)))
    print(files)
    for filename in files:
        parse(filename)
