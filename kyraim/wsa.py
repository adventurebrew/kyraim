import os
from pathlib import Path
from typing import Mapping

import numpy as np
from PIL import Image
from kyraim.codex.base import read_uint16_le, read_uint32_le
from kyraim.codex.lcw import decode_lcw
from kyraim.codex.xor_delta import compress_xor_buffer, decompress_xor_buffer

from kyraim.texts import match_archive_files
from kyraim.cps import GameCPSDef, decode_cps, read_palette


WSA_FLAGS = {
    'WF_OFFSCREEN_DECODE': 0x10,
    'WF_NO_LAST_FRAME': 0x20,
    'WF_NO_FIRST_FRAME': 0x40,
    'WF_FLIPPED': 0x80,
    'WF_HAS_PALETTE': 0x100,
    'WF_XOR': 0x200,
}


def decode_wsa_sequence(stream, palette, version='kyra'):
    # https://moddingwiki.shikadi.net/wiki/Westwood_WSA_Format
    # UINT16LE	NrOfFrames	Number of frames.
    # UINT16LE	XPos	X-offset of the frame data. This field does not appear in the Dune II versions of the format.
    # UINT16LE	YPos	Y-offset of the frame data. This field does not appear in the Dune II versions of the format.
    # UINT16LE	Width	Width of the frames.
    # UINT16LE	Height	Height of the frames.
    # UINT16LE	DeltaBufferSize	Size of the buffer required to unpack the frame data. Through some development quirk, this value is always 37 bytes smaller than the actual required buffer size. This field is a UINT32LE in the Monopoly version of the format.
    # UINT16LE	Flags	Extra load options. The only available option is HasPalette, which is bit 1. This field does not appear in the Dune II v1.00 version of the format, meaning that version can never have an embedded palette.
    # UINT32LE[NrOfFrames+2]	FrameOffsets	Addresses of the frame offsets. The addresses are relative to the start of the file, but do not take the palette into account, meaning that if the HasPalette flag is enabled, 768 bytes need to be added to these offsets to find the actual data.
    # BYTE[768]	Palette	A 256-colour 6-bit RGB VGA palette. Only occurs if the HasPalette flag is enabled. This is an 8-bit RGB VGA palette in the Monopoly version of the format.

    num_frames = read_uint16_le(stream)

    if version == 'kyra2':
        _xpos = read_uint16_le(stream)
        _ypos = read_uint16_le(stream)

    width = read_uint16_le(stream)
    height = read_uint16_le(stream)
    lcw_buffer_size = read_uint16_le(stream)
    flags = read_uint16_le(stream)
    offs = [read_uint32_le(stream) for _ in range(num_frames + 1)]
    file_size = read_uint32_le(stream)

    has_palette = flags & 1

    if has_palette:
        palette = read_palette(stream)

    print(num_frames, width, height, lcw_buffer_size, flags)
    # print(xpos, ypos)
    print(offs)

    frame = np.zeros((height, width), dtype=np.uint8)
    lcw_buffer = b'\0' * lcw_buffer_size

    for off in offs:
        assert stream.tell() == off + has_palette * len(palette), (
            stream.tell(),
            off + has_palette * len(palette),
        )
        lcw_buffer = b'\0' * lcw_buffer_size

        if off == offs[-1] and file_size == 0:  # kyra2
            break
        lcw_buffer = decode_lcw(stream, lcw_buffer, lcw_buffer_size)

        old_frame = np.array(frame, dtype=np.uint8)  # for verification

        uncomp = decompress_xor_buffer(lcw_buffer)
        comp = compress_xor_buffer(
            uncomp,
            # bytes(lcw_buffer)
        )
        assert decompress_xor_buffer(comp) == uncomp
        # assert comp == bytes(lcw_buffer), (comp, bytes(lcw_buffer))

        decoded_xor = np.frombuffer(
            decompress_xor_buffer(lcw_buffer), dtype=np.uint8
        )
        _rest = decoded_xor[height * width:]
        # assert len(rest) == 0 or np.all(rest == 0), rest
        decoded_xor = decoded_xor[:height * width].reshape(height, width)
        frame ^= decoded_xor

        assert np.array_equal(decoded_xor, frame ^ old_frame)
        im = Image.fromarray(frame.reshape(height, width), mode='P')
        if palette:
            im.putpalette(palette)
        yield im, has_palette

    assert stream.read() == b''
    if file_size != 0:
        assert stream.tell() == file_size, (stream.tell(), file_size)


GAMES: Mapping[str, GameCPSDef] = {
    'kyra': {
        'palettes': [
            'TOP.CPS',
            'ORIGPAL.COL',
            'TREE_EXP.COL',
        ],
        'patterns': {
            'KYRANDIA.WSA': ['TOP.CPS'],
            'AMULET.WSA': ['TREE_EXP.COL'],
            'RAISEPIC.WSA': ['ORIGPAL.COL'],
            'RINGBELL.WSA': ['ORIGPAL.COL'],
            'BONK.WSA': ['TREE_EXP.COL'],
            'NEEDSAW1.WSA': ['ORIGPAL.COL'],
            'AGILE.WSA': ['ORIGPAL.COL'],
            'ADVICE.WSA': ['ORIGPAL.COL'],
            'BALANCE2.WSA': ['ORIGPAL.COL'],
            'RIDGE.WSA': ['ORIGPAL.COL'],
            'RIDGE2.WSA': ['ORIGPAL.COL'],
            'EYES.WSA': ['ORIGPAL.COL'],  #
            'ACIDGATE.WSA': ['ORIGPAL.COL'],
            'GATE.WSA': ['ORIGPAL.COL'],
            'PLANT.WSA': ['ORIGPAL.COL'],
            'PLANT2.WSA': ['ORIGPAL.COL'],
            'SLIDE1.WSA': ['ORIGPAL.COL'],
            'SLIDE2.WSA': ['ORIGPAL.COL'],
            'UPSTAIRS.WSA': ['ORIGPAL.COL'],
            'DNSTAIRS.WSA': ['ORIGPAL.COL'],
            'TOSS.WSA': ['ORIGPAL.COL'],
            'MALENTER.WSA': ['ORIGPAL.COL'],
            'SHUFFLE2.WSA': ['ORIGPAL.COL'],
            'JUGGLE.WSA': ['ORIGPAL.COL'],
            'JUGLTALK.WSA': ['ORIGPAL.COL'],
            'BEHIND.WSA': ['ORIGPAL.COL'],
            'JESTTALK.WSA': ['ORIGPAL.COL'],
            'BRANTALK.WSA': ['ORIGPAL.COL'],
            'DODGE.WSA': ['ORIGPAL.COL'],
            'SEALED.WSA': ['ORIGPAL.COL'],
            'SHATTER.WSA': ['ORIGPAL.COL'],
            'FROZEN.WSA': ['ORIGPAL.COL'],
            'FROG.WSA': ['ORIGPAL.COL'],
            'FINALA.WSA': ['ORIGPAL.COL'],
            'FINALB.WSA': ['ORIGPAL.COL'],
            'FINALC.WSA': ['ORIGPAL.COL'],
            'FINALD.WSA': ['ORIGPAL.COL'],
            'REUNION.WSA': ['ORIGPAL.COL'],
            'CHALICE1.WSA': ['ORIGPAL.COL'],
            'CHALICE2.WSA': ['ORIGPAL.COL'],
            'STEAL1.WSA': ['ORIGPAL.COL'],
            'TAG-0.WSA': ['ORIGPAL.COL'],
            'TAG.WSA': ['ORIGPAL.COL'],
            'FOUNTAN1.WSA': ['TEMP.COL'],
            'FOUNTAN2.WSA': ['TEMP.COL'],
            'FNTTALK.WSA': ['TEMP.COL'],
            'FOYER.WSA': ['ORIGPAL.COL'],
            'PUNCH1.WSA': ['ORIGPAL.COL'],
            'PUNCH2.WSA': ['ORIGPAL.COL'],
            'PUNCH3.WSA': ['ORIGPAL.COL'],
            'CAVEDOOR.WSA': ['ORIGPAL.COL'],
            'ROCKS1.WSA': ['ORIGPAL.COL'],
            'ROCKS2.WSA': ['ORIGPAL.COL'],
            'ROCKS3.WSA': ['ORIGPAL.COL'],
            'ROCKS4.WSA': ['ORIGPAL.COL'],
            'ROCKS5.WSA': ['ORIGPAL.COL'],
            'LIFTDWN.WSA': ['ORIGPAL.COL'],
            'LIFTUP.WSA': ['ORIGPAL.COL'],
            'GRANDPA.WSA': ['ORIGPAL.COL'],
            'BRANTREE.WSA': ['ORIGPAL.COL'],
            'FACE.WSA': ['ORIGPAL.COL'],
            'FACE2.WSA': ['ORIGPAL.COL'],
            'TOUCH.WSA': ['ORIGPAL.COL'],
            'HERSAW1.WSA': ['ORIGPAL.COL'],
            'HERSAW2.WSA': ['ORIGPAL.COL'],
            'HERSAW3.WSA': ['ORIGPAL.COL'],
            'LEP_OUT.WSA': ['ORIGPAL.COL'],
            'LEP_IN.WSA': ['ORIGPAL.COL'],
            'MOTHER1.WSA': ['ORIGPAL.COL'],
            'MOTHER2.WSA': ['ORIGPAL.COL'],
            'BRNENTR.WSA': ['ORIGPAL.COL'],
            'BRYNN1.WSA': ['ORIGPAL.COL'],
            'BRYNN2.WSA': ['ORIGPAL.COL'],
            'BRYNN3.WSA': ['ORIGPAL.COL'],
            'WESTWOOD.WSA': ['WESTWOOD.COL'],
            'SHORE.WSA': ['ORIGPAL.COL'],
            'TREE1.WSA': ['ORIGPAL.COL'],
            'TREE2.WSA': ['ORIGPAL.COL'],
            'KALLAK.WSA': ['KALLAK.COL'],
            'MAL-KAL.WSA': ['MAL-KAL.COL'],
            'PEGASUS.WSA': ['ORIGPAL.COL'],
            'WILOFISH.WSA': ['ORIGPAL.COL'],
            'LANDING.WSA': ['ORIGPAL.COL'],
            'BRANBRN.WSA': ['ORIGPAL.COL'],
            'JUMP.WSA': ['ORIGPAL.COL'],
            'LEPCLIMB.WSA': ['ORIGPAL.COL'],
            'LEPHOLE.WSA': ['ORIGPAL.COL'],
            'FIREPLACE.WSA': ['ORIGPAL.COL'],
            'MIXROX.WSA': ['ORIGPAL.COL'],  #
            'MOONCAV1.WSA': ['ORIGPAL.COL'],
            'MOONCAV2.WSA': ['ORIGPAL.COL'],
            'ZANBASIC.WSA': ['ORIGPAL.COL'],
            'BRANZAN.WSA': ['ORIGPAL.COL'],
            'ZANDOORU.WSA': ['ORIGPAL.COL'],
            'ZANDOORD.WSA': ['ORIGPAL.COL'],
            'WAKEN.WSA': ['ORIGPAL.COL'],
            'LAUNDRY.WSA': ['ORIGPAL.COL'],
            'POUR.WSA': ['ORIGPAL.COL'],
            'CARPET.WSA': ['ORIGPAL.COL'],
            'SNGSPELL.WSA': ['ORIGPAL.COL'],
            'SONG1.WSA': ['ORIGPAL.COL'],
            'RAINDROP.WSA': ['ORIGPAL.COL'],
            'BRANDYW1.WSA': ['ORIGPAL.COL'],
            'BRANDYW2.WSA': ['ORIGPAL.COL'],
            'BRANDYW3.WSA': ['ORIGPAL.COL'],
            'SPELL.WSA': ['ORIGPAL.COL'],
            'CTRAP1.WSA': ['ORIGPAL.COL'],
            'CTRAP2.WSA': ['ORIGPAL.COL'],
            'ALTER.WSA': ['ORIGPAL.COL'],
            'DROPDOWN.WSA': ['ORIGPAL.COL'],
            'DROPUP.WSA': ['ORIGPAL.COL'],
            'WOW.WSA': ['ORIGPAL.COL'],
            'SAW.WSA': ['ORIGPAL.COL'],
        },
    },
    'kyra2': {
        'palettes': [
            # 'PALETTE.COL',
        ],
        'patterns': {
            'TITLE.WSA': [],
        },
    },
}


if __name__ == '__main__':
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

    args = parser.parse_args()

    palettes = {}
    patterns = GAMES[args.game]

    frames_dir = Path('frames')

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
        print(bname)

    for pak, pattern, fname in match_archive_files(
        args.directory, patterns['patterns']
    ):
        bname = os.path.basename(fname)
        os.makedirs(frames_dir / bname, exist_ok=True)
        print(fname, pattern)
        with pak.open(fname, 'rb') as fstream:
            for idx, (im, has_palette) in enumerate(
                decode_wsa_sequence(fstream, b'', version=args.game)
            ):
                if has_palette:
                    im.save(frames_dir / bname / f'frame_{idx:05d}.png')
                else:
                    for palpat in patterns['patterns'][pattern]:
                        for palname in palettes:
                            if Path(palname).match(palpat):
                                im.putpalette(palettes[palname])
                                im.save(
                                    frames_dir
                                    / bname
                                    / f'frame_{idx:05d}.{palname}.png'
                                )
