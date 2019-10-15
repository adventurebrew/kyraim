import glob

from chunk import Chunk
from itertools import chain, takewhile
from functools import partial

def read_uint16_be(stream) -> int: 
    return int.from_bytes(stream.read(2), byteorder='big', signed=False)

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
    return b''.join(iter(partial(stream.read, 1), b'\00')).decode()

def parse(fname):
    print(fname)
    with open(fname, 'rb') as stream:
        form = Chunk(stream)
        assert form.getname() == b'FORM'
        assert form.read(4) == b'EMC2'
        # chunks = list(read_chunks(form))
        # for c in chunks:
        #     c.seek(0)
        #     print(c.getname(), c.read())
        # exit(1)
        for idx, chunk in enumerate(read_chunks(form)):
            # print(chunk.getname(), chunk.chunksize)
            chunk.seek(0)
            if chunk.getname() == b'TEXT':
                start = read_uint16_be(chunk)
                read_offsets = iter(partial(read_uint16_be, chunk), b'')
                offs = list(takewhile(partial(before_offset, chunk, start), read_offsets))
                for off in chain([start], offs):
                    # assert chunk.tell() == off, (chunk.tell(), off)
                    chunk.seek(off)
                    print(fname + '\t"' + readcstr(chunk) + '"')

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('files', nargs='+', help='files to extract')
    args = parser.parse_args()

    files = sorted(set(chain.from_iterable(glob.iglob(r) for r in args.files)))
    print(files)
    for filename in files:
        parse(filename)
