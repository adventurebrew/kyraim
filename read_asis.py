import glob

from itertools import chain
import os

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('files', nargs='+', help='files to extract')
    args = parser.parse_args()

    files = sorted(set(chain.from_iterable(glob.iglob(r) for r in args.files)))
    print(files)
    with open('more-lost-strs6.txt', 'w', encoding='utf-8', errors='escape') as output_file:
        for filename in files:
            with open(filename, 'r', encoding='latin-1', errors='escape') as inf:
                text = inf.read().replace('"', '`')
            print(os.path.basename(filename), f'"{text}"', sep='\t', file=output_file)
