import glob

from itertools import chain
import itertools
import operator
import os


def split_lines(lines):
    for line in lines:
        fname, line = line[:-1].split('\t', maxsplit=1)
        yield fname, line

def compose(fname):
    # print(fname)
    with open(fname, 'r', encoding='windows-1255', errors='ignore') as f:
        grouped = itertools.groupby(split_lines(f), key=operator.itemgetter(0))
        for tfname, group in grouped:
            basename = os.path.basename(tfname)
            lines_in_group = [line for _, line in group]

            assert len(lines_in_group) == 1

            text = (lines_in_group[0] + '~~~').replace('~~~', '\r\n')

            os.makedirs('book_patch', exist_ok=True)
            with open(os.path.join('book_patch', basename), 'wb') as res:
                res.write(text.encode('cp862') + b'\x1a')
                # if not res.tell() % 2:
                #     res.write(b'\x00\x00')



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('files', nargs='+', help='files to extract')
    args = parser.parse_args()

    files = sorted(set(chain.from_iterable(glob.iglob(r) for r in args.files)))
    print(files)
    for filename in files:
        compose(filename)
