import io
import os
from enum import IntEnum
from pathlib import Path
from typing import IO, Mapping, Optional, Sequence, Tuple, TypedDict

import numpy as np
from PIL import Image

from kyraim.codex.base import read_int8, read_uint16_be, read_uint16_le, read_uint32_le
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

    elif comp == Compression.RLE:
        buffer = bytearray(img_size)
        dst = 0
        while dst < img_size:
            code = read_int8(stream)
            if code == 0:
                sz = read_uint16_be(stream)
                buffer[dst:dst+sz] = stream.read(1) * sz
                dst += sz
            elif code < 0:
                buffer[dst:dst-code] = stream.read(1) * -code
                dst += -code
            else:
                buffer[dst:dst+code] += stream.read(code)
                dst += code
        im = bytes(buffer)

    else:
        raise NotImplementedError(comp)

    diff = stream.tell() - file_size
    assert 0 <= diff < 2 , (stream.tell(), file_size)
    rest = stream.read()
    assert rest == b'\x80' * diff, rest
    # assert not rest, rest

    return im, palette


class GameCPSDef(TypedDict):
    palettes: Sequence[str]
    patterns: Mapping[str, Sequence[str]]


GAMES: Mapping[str, GameCPSDef] = {
    'kyra': {
        'palettes': [
            'TOP.CPS',
            'GEMHEALS.CPS',
            'REUNION.CPS',
            'CHALET.CPS',
            'ORIGPAL.COL',
            'KALLAK.COL',
            'TEMP.COL',
            'WESTWOOD.COL',
            'KYRANDIA.COL',
            'TREE_EXP.COL',
            'MAL-KAL.COL',
            'TOP.PAL',
            # '*.COL'
            # '*.CPS',
        ],
        'patterns': {
            'MAIN_*.CPS': ['TOP.CPS'],
            'TEXT_*.CPS': ['TOP.CPS'],
            'ALCHEMY.CPS': ['ORIGPAL.COL'],
            'ALGAE.CPS': ['TEMP.COL'],
            'ALTAR.CPS': ['top.pal'],
            'ARCH.CPS': ['TEMP.COL'],
            'BALCONY.CPS': ['KYRANDIA.COL'],
            'BELROOM.CPS': ['ORIGPAL.COL'],
            'BONKBG.CPS': ['TREE_EXP.COL'],
            'BRIDGE.CPS': ['ORIGPAL.COL'],
            'BRINS.CPS': ['ORIGPAL.COL'],
            'BROKEN.CPS': ['ORIGPAL.COL'],
            'BURN.CPS': ['KYRANDIA.COL'],
            'CASTLE.CPS': ['KYRANDIA.COL'],  # palette?
            'CATACOM.CPS': ['TEMP.COL'],  # palette?
            'CAVE.CPS': ['TREE_EXP.COL'],
            'CAVEB.CPS': ['TREE_EXP.COL'],
            'CGATE.CPS': ['TEMP.COL'],  # palette?
            'CHASM.CPS': ['ORIGPAL.COL'],
            'CLIFF.CPS': ['ORIGPAL.COL'],  # aplette?
            'DARMS.CPS': ['ORIGPAL.COL'],
            'DEAD.CPS': ['ORIGPAL.COL'],  # palette?
            'DNSTAIR.CPS': ['TEMP.COL'],
            'DRAGON.CPS': ['ORIGPAL.COL'],
            'EDGE.CPS': ['TREE_EXP.COL'],
            'EDGEB.CPS': ['TREE_EXP.COL'],
            'EMCAV.CPS': ['bottom.COL'],  # palette!
            'ENTER.CPS': ['ORIGPAL.COL'],
            'EXTHEAL.CPS': ['WESTWOOD.COL'],  # palette?
            'EXTPOT.CPS': ['WESTWOOD.COL'],  # palette?
            'EXTSPEL.CPS': ['WESTWOOD.COL'],
            'FALLS.CPS': ['TREE_EXP.COL'],
            'FESTSTH.CPS': ['TREE_EXP.COL'],
            'FGOWEST.CPS': ['TREE_EXP.COL'],
            'GEMHEALS.CPS': ['GEMHEALS.CPS'],
            'CHALET.CPS': ['CHALET.CPS'],
            'BEAD.CPS': ['CHALET.CPS'],
            'REUNION.CPS': ['REUNION.CPS'],
            'FNORTH.CPS': ['TREE_EXP.COL'],
            'FORESTA.CPS': ['TREE_EXP.COL'],
            'FORESTB.CPS': ['TREE_EXP.COL'],
            'FORESTC.CPS': ['TREE_EXP.COL'],
            'FOUNTN.CPS': ['TEMP.COL'],
            'FOYER.CPS': ['TEMP.COL'],
            'FSOUTH.CPS': ['TREE_EXP.COL'],
            'FSOUTHB.CPS': ['TREE_EXP.COL'],
            'FWSTSTH.CPS': ['TREE_EXP.COL'],
            'GATECV.CPS': ['ORIGPAL.COL'],
            'GEM.CPS': ['WESTWOOD.COL'],
            'GEMCUT.CPS': ['WESTWOOD.COL'],
            'GENCAVB.CPS': ['TREE_EXP.COL'],  # palette?
            'GENHALL.CPS': ['WESTWOOD.COL'],
            'GEN_CAV.CPS': ['TREE_EXP.COL'],  # palette?
            'GLADE.CPS': ['WESTWOOD.COL'],
            'GRAVE.CPS': ['ORIGPAL.COL'],
            'GRTHALL.CPS': ['ORIGPAL.COL'],
            'HEALER.CPS': ['ORIGPAL.COL'],
            'TOP.CPS': ['TOP.CPS'],
            'BOTTOM.CPS': ['BOTTOM.CPS'],
            'TREE.CPS': ['TREE_EXP.CPS'],
            'WRITING.CPS': ['KALLAK.COL'],
            'GEMCUTI.CPS': ['MAL-KAL.COL'],
            'KITCHEN.CPS': ['ORIGPAL.COL'],
            'KYRAGEM.CPS': ['TREE_EXP.COL'],
            'LAGOON.CPS': ['WESTWOOD.COL'],  # palette!
            'LANDING.CPS': ['ORIGPAL.COL'],
            'LAVA.CPS': ['TREE_EXP.COL'],  # palette!
            'LEPHOLE.CPS': ['ORIGPAL.COL'],
            'LIBRARY.CPS': ['ORIGPAL.COL'],
            'MAIN_GER.CPS': ['ORIGPAL.COL'],
            'FLUTE1.CPS': ['ORIGPAL.COL'],
            'FLUTE2.CPS': ['ORIGPAL.COL'],
            'SNOW1A.CPS': ['ORIGPAL.COL'],
            'SNOW2A.CPS': ['ORIGPAL.COL'],
            'TELEKIN.CPS': ['ORIGPAL.COL'],
            'HEALBR1.CPS': ['ORIGPAL.COL'],
            'NOTEGER.CPS': ['ORIGPAL.COL'],
            'DRINK.CPS': ['ORIGPAL.COL'],
            'AMULET3.CPS': ['ORIGPAL.COL'],
            'BRANSTON.CPS': ['ORIGPAL.COL'],
            'HEALBR2.CPS': ['ORIGPAL.COL'],
            'POISON.CPS': ['ORIGPAL.COL'],
            'MIX.CPS': ['ORIGPAL.COL'],
            'MOONCAV.CPS': ['TREE_EXP.COL'],  # palette!
            'NCLIFF.CPS': ['ORIGPAL.COL'],  # palette!
            'NCLIFFB.CPS': ['ORIGPAL.COL'],  # palette!
            'NWCLIFFB.CPS': ['ORIGPAL.COL'],  # palette!
            'NWCLIFF.CPS': ['ORIGPAL.COL'],  # palette!
            'OAKS.CPS': ['ORIGPAL.COL'],
            'PLATEAU.CPS': ['ORIGPAL.COL'],
            'PLTCAVE.CPS': ['ORIGPAL.COL'],
            'POTION.CPS': ['ORIGPAL.COL'],  # palette?
            'RUBY.CPS': ['TREE_EXP.COL'],
            'SICKWIL.CPS': ['TREE_EXP.COL'],
            'SONG.CPS': ['TREE_EXP.COL'],
            'SORROW.CPS': ['top.pal'],
            'SPELL.CPS': ['ORIGPAL.COL'],
            'SPRING.CPS': ['TREE_EXP.COL'],
            'SQUARE.CPS': ['TREE_EXP.COL'],  # palette?
            'BRANDON.CPS': ['PALETTE.COL'],
            'BRANWILL.CPS': ['PALETTE.COL'],
            'BUTTONS2.CPS': ['PALETTE.COL'],
            'EFFECTS.CPS': ['PALETTE.COL'],
            'HERMAN.CPS': ['PALETTE.COL'],
            'ITEMS.CPS': ['PALETTE.COL'],
            'JEWELS3.CPS': ['PALETTE.COL'],
            'MOUSE.CPS': ['PALETTE.COL'],
            'MERITH.CPS': ['PALETTE.COL'],
            'STUMP.CPS': ['WESTWOOD.COL'],
            'TEMPLE.CPS': ['ORIGPAL.COL'],
            'TEXT_GER.CPS': ['ORIGPAL.COL'],
            'TRUNK.CPS': ['ORIGPAL.COL'],
            'UPSTAIRS.CPS': ['WESTWOOD.COL'],
            'WELL.CPS': ['ORIGPAL.COL'],
            'WILLOW.CPS': ['ORIGPAL.COL'],
            'WISE.CPS': ['ORIGPAL.COL'],
            'XEDGE.CPS': ['ORIGPAL.COL'],
            'XEDGEB.CPS': ['ORIGPAL.COL'],
            'XEDGEC.CPS': ['ORIGPAL.COL'],
            'ZROCK.CPS': ['ORIGPAL.COL'],  # palette!
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

    graphics_dir = Path('graphics')
    os.makedirs(graphics_dir, exist_ok=True)

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
                bim.save(graphics_dir / f'{bname}.png')
            else:
                for palpat in patterns['patterns'][pattern]:
                    for palname in palettes:
                        if Path(palname).match(palpat):
                            bim.putpalette(npal or palettes[palname])
                            bim.save(graphics_dir / f'{bname}.{palname}.png')
