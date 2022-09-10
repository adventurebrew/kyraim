import io
import os
from enum import IntEnum
from pathlib import Path
from typing import IO, Mapping, Optional, Sequence, Tuple, TypedDict

import numpy as np
from PIL import Image

from kyraim.codex.base import read_uint16_le, read_uint32_le
from kyraim.codex.lcw import decode_lcw, encode_lcw
from kyraim.texts import match_archive_files


skip = False


class Compression(IntEnum):
    LZW_12 = 1
    LZW_14 = 2
    RLE = 3
    LCW = 4


# palette = [((53 + x) ** 2 * 13 // 5) % 256 for x in range(256 * 3)]


def read_palette(stream: IO[bytes]) -> bytes:
    return bytes(((x << 2) | (x & 3)) % 256 for x in stream.read(0x300))


def decode_cps(
    stream: IO[bytes],
    palette: Optional[bytes],
    skip: bool = False,
    verify: bool = False,
    decode: bool = True,
) -> Tuple[bytes, Optional[bytes]]:
    if skip:
        print('SKIP', stream.read(4))

    file_size = read_uint16_le(stream)
    comp = read_uint16_le(stream)
    img_size = read_uint32_le(stream)
    palen = read_uint16_le(stream)
    print(comp, img_size, palen)

    if palen == 0x300:
        palette = read_palette(stream)

    if not decode:
        return stream.read(), palette

    if comp == Compression.LCW:
        pos = stream.tell()
        im = decode_lcw(stream, b'\0' * img_size, img_size)

        if verify:
            pos2 = stream.tell()
            stream.seek(pos)
            orig = stream.read(pos2 - pos)
            stream.seek(pos2)
            compr = encode_lcw(im)

            # # HARD COMPARISON
            # assert compr == orig
            # for i in range(200):
            #     if compr[i*320:(i+1)*320] != orig[i*320:(i+1)*320]:
            #         print(len(compr[i*320:(i+1)*320]), compr[i*320:(i+1)*320])
            #         print(len(orig[i*320:(i+1)*320]), orig[i*320:(i+1)*320])
            #         exit(1)

            # SOFT COMPARISON
            with io.BytesIO(compr) as ins:
                print('====================')
                uncomp = decode_lcw(ins, b'\0' * img_size, img_size)
                assert im == uncomp, (im, uncomp)

    else:
        raise NotImplementedError(comp)

    # # TODO: replace with +2 if adding trailing 0x80
    assert stream.tell() == file_size + 1, (stream.tell(), file_size)
    rest = stream.read()
    assert rest == b'\x80', rest
    # assert not rest, rest

    return im, palette


class GameCPSDef(TypedDict):
    palettes: Sequence[str]
    patterns: Mapping[str, Sequence[str]]


GAMES: Mapping[str, GameCPSDef] = {
    'kyra': {
        'palettes': [
            'TOP.CPS',
            # '*.CPS',
        ],
        'patterns': {
            'MAIN_*.CPS': ['TOP.CPS'],
            'TEXT_*.CPS': ['TOP.CPS'],
            # '*.CPS': ['*.CPS'],
        },
    },
    'kyra2': {
        'palettes': [
            # '*.COL',
            # '*.CPS',
        ],
        'patterns': {
            # '*.CPS': [
            #     '*.COL',
            #     '*.CPS',
            # ],
        },
    },
}


if __name__ == '__main__':

    width, height = 320, 200
    import argparse

    parser = argparse.ArgumentParser(description='extract pak archive')
    parser.add_argument('directory', help='files to extract')
    parser.add_argument(
        '--game',
        '-g',
        choices=GAMES,
        required=True,
        help='Use specific game pattern',
    )
    parser.add_argument(
        '--check',
        '-c',
        action='store_true',
        default=False,
        required=False,
        help='Verify re-encoded decompresses to same image',
    )
    args = parser.parse_args()

    palettes = {}
    patterns = GAMES[args.game]

    for pak, pattern, fname in match_archive_files(
        args.directory, patterns['palettes']
    ):
        bname = os.path.basename(fname)
        with pak.open(fname, 'rb') as stream:
            palette = None
            if Path(bname).match('*.CPS'):
                _, palette = decode_cps(stream, None, decode=False)
            elif Path(bname).match('*.COL'):
                palette = read_palette(stream)
            if palette:
                palettes[bname] = palette

    for pak, pattern, fname in match_archive_files(
        args.directory, patterns['patterns']
    ):
        bname = os.path.basename(fname)
        print(fname, pattern)
        with pak.open(fname, 'rb') as fstream:
            im, npal = decode_cps(fstream, palette, verify=args.check)
            im += b'\0' * width * height
            bim = Image.fromarray(
                np.frombuffer(im, dtype=np.uint8)[: width * height].reshape(
                    height,
                    width,
                ),
                mode='P',
            )
            if npal:
                bim.putpalette(npal or palettes[patterns['patterns'][pattern]])
                bim.save(f'{bname}.png')
            else:
                for palpat in patterns['patterns'][pattern]:
                    for palname in palettes:
                        if Path(palname).match(palpat):
                            bim.putpalette(npal or palettes[palname])
                            bim.save(f'{bname}.{palname}.png')
