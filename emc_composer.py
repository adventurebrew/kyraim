import glob

from chunk import Chunk
from itertools import chain, groupby, takewhile
from functools import partial
import itertools
import operator

def read_uint16_be(stream) -> int: 
    return int.from_bytes(stream.read(2), byteorder='big', signed=False)


def write_uint16_be(num) -> int: 
    return num.to_bytes(2, byteorder='big', signed=False)


def write_uint32_be(num) -> int: 
    return num.to_bytes(4, byteorder='big', signed=False)


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
                assert offs == sorted(offs), offs
                for off in chain([start], offs):
                    # assert chunk.tell() == off, (chunk.tell(), off)
                    chunk.seek(off)
                    print(fname, f'"{readcstr(chunk)}"', sep='\t')

def wrap_chunk(tag, data, size_fix=0):
    return tag + write_uint32_be(len(data) + size_fix) + data

def split_lines(lines):
    for line in lines:
        fname, line = line[:-1].split('\t')
        yield fname, line

VERIFY = False

if __name__ == "__main__":
    import argparse
    import os
    import re

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('files', nargs='+', help='files to extract')
    args = parser.parse_args()

    files = sorted(set(chain.from_iterable(glob.iglob(r) for r in args.files)))
    # print(files)
    # for filename in files:
    #     parse(filename)

    for filename in files:
        with open(filename, 'r') as f:
            grouped = itertools.groupby(split_lines(f), key=operator.itemgetter(0))
            for fname, group in grouped:
                lines_in_group = [line for _, line in group][1:]
                nfname = os.path.join('patch', fname)
                os.makedirs(os.path.dirname(nfname), exist_ok=True)
                print(nfname, lines_in_group)

                data = bytearray(b'EMC2')
                with open(os.path.join('orig', fname), 'rb') as orig, open(nfname, 'wb') as out:
                    form = Chunk(orig)
                    assert form.getname() == b'FORM'
                    assert form.read(4) == b'EMC2'
                    for idx, chunk in enumerate(read_chunks(form)):
                        chunk.seek(0)
                        if chunk.getname() == b'TEXT':

                            start = read_uint16_be(chunk)
                            read_offsets = iter(partial(read_uint16_be, chunk), b'')
                            orig_offs = list(takewhile(partial(before_offset, chunk, start), read_offsets))

                            for off in chain([start], orig_offs):
                                chunk.seek(off)
                                print('ORIG', fname, f'"{readcstr(chunk)}"', sep='\t')


                            base = len(lines_in_group) * 2

                            if VERIFY:
                                assert base == start, (base, start)

                            text = '\0'.join(lines_in_group)
                            print([repr(line) for line in lines_in_group])
                            offs = [base] + [m.start() + base + 1 for m in re.finditer('\0', text)]
                            print(offs)
                            print(text)

                            if VERIFY:
                                assert [start] + orig_offs == offs, ([start] + orig_offs, offs)

                            chunk_data = b''.join(write_uint16_be(off) for off in offs) + text.encode('cp862') + b'\0'
                            
                            data += wrap_chunk(b'TEXT', chunk_data)

                            if len(data) % 2:
                                data += b'\0'
                        else:
                            data += wrap_chunk(chunk.getname(), chunk.read())
                            if len(data) % 2:
                                data += b'\0'
                            # start = read_uint16_be(chunk)
                            # read_offsets = iter(partial(read_uint16_be, chunk), b'')
                            # offs = list(takewhile(partial(before_offset, chunk, start), read_offsets))
                            # assert offs == sorted(offs), offs
                            # for off in chain([start], offs):
                            #     # assert chunk.tell() == off, (chunk.tell(), off)
                            #     chunk.seek(off)
                            #     print(fname, f'"{readcstr(chunk)}"', sep='\t')
                    data = bytes(data)
                    final_data = wrap_chunk(b'FORM', data, 8)
                    out.write(final_data)
                    if VERIFY:
                        form.seek(0)
                        orig_data = form.read()
                        if orig_data != data:
                            for i in range(500):
                                left, right = orig_data[50 * i:][:50], data[50 * i:][:50]
                                if left != right:
                                    print('DIFF', left, right)
                                else:
                                    if left:
                                        print(left)
                            print('exiting...')
                            exit(1)
                        assert orig_data == data, (repr(orig_data) + '\n' + repr(data))
                        orig.seek(0)
                        orig_complete = orig.read()
                        assert final_data == orig_complete, (final_data[:12], orig_complete[:12])
