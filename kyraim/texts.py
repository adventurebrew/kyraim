import csv
import io
import os
from pathlib import Path

from kyraim.archive import pakfile, installer
from kyraim.codex.texts import asis, ccode, dlg, emc, tre


ARCHIVE_PATTERN = '*.PAK'
INSTALLER_PATTERN = 'WESTWOOD.001'


KYRA_TEXTS = {
    '*.EMC': ('emc', emc.write_parsed, emc.compose),
}


KYRA2_TEXTS = {
    **KYRA_TEXTS,
    '*.DLE': ('dlg', dlg.write_parsed, dlg.compose),
    'LETTER*.ENG': ('asis', asis.write_parsed, asis.compose),
    'PAGE*.ENG': ('asis', asis.write_parsed, asis.compose),
    '*.ENG': ('ccode', ccode.write_parsed, ccode.compose),
}


KYRA3_TEXTS = {
    '*.TRE': ('tre', tre.write_parsed, tre.compose),
}


GAMES = {
    'all': {**KYRA_TEXTS, **KYRA2_TEXTS, **KYRA3_TEXTS},
    'kyra': KYRA_TEXTS,
    'kyra2': KYRA2_TEXTS,
    'kyra3': KYRA3_TEXTS,
}


def match_archive_files(path, patterns):
    parsed_files = set()
    path = Path(path)

    for text_pattern in patterns:
        for fname in path.glob(text_pattern):
            if fname not in parsed_files:
                parsed_files.add(fname)
                yield io, text_pattern, fname

    for archive in sorted(path.glob(ARCHIVE_PATTERN)):
        with pakfile.open(archive) as f:
            for fname in f.index:
                for text_pattern in patterns:
                    if Path(fname).match(text_pattern):
                        if fname not in parsed_files:
                            parsed_files.add(fname)
                            yield f, text_pattern, fname

    for inst in sorted(path.glob(INSTALLER_PATTERN)):
        with installer.open(inst) as ins:
            for text_pattern in patterns:
                for fname in ins.glob(text_pattern):
                    if fname not in parsed_files:
                        parsed_files.add(fname)
                        yield ins, text_pattern, fname

            archives = ins.glob(ARCHIVE_PATTERN)
            for archive in archives:
                with ins.open(archive, 'rb') as pakstream:
                    with pakfile.open(pakstream) as f:
                        for fname in f.index:
                            for text_pattern in patterns:
                                if Path(fname).match(text_pattern):
                                    if fname not in parsed_files:
                                        parsed_files.add(fname)
                                        yield f, text_pattern, fname


def decode(patterns, path):
    open_files = set()
    for pak, pattern, fname in match_archive_files(path, patterns):
        agg_file, parse, _ = patterns[pattern]
        with pak.open(fname, 'rb') as stream:
            text_file = texts_dir / (agg_file + '.tsv')
            mode = 'a' if agg_file in open_files else 'w'
            with open(text_file, mode, encoding='utf-8') as out:
                open_files.add(agg_file)
                parse(fname, stream, out)

                os.makedirs('orig', exist_ok=True)
                stream.seek(0)
                (Path('orig') / os.path.basename(fname)).write_bytes(stream.read())


def encode(patterns):
    encoders = set((name, composer) for _, (name, _, composer) in patterns.items())
    for agg_file, composer in encoders:
        text_file = texts_dir / (agg_file + '.tsv')
        if not text_file.exists():
            continue
        with open(text_file, 'r', encoding='utf-8') as f:
            tsv_file = csv.reader(f, delimiter='\t')
            composer(tsv_file, target='patch')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('directory', help='files to extract')
    parser.add_argument(
        '--game',
        '-g',
        choices=GAMES,
        default='all',
        help='Use specialized game pattern',
    )
    parser.add_argument(
        '--rebuild',
        '-r',
        action='store_true',
        help='create modifed game resource with the changes',
    )
    args = parser.parse_args()

    patterns = GAMES[args.game]

    texts_dir = Path('texts')
    os.makedirs(texts_dir, exist_ok=True)

    if not args.rebuild:
        decode(patterns, args.directory)
    else:
        encode(patterns)
