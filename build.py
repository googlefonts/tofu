""" Make a font with a "tofu" .notdef glyph

Ref https://github.com/fonttools/fonttools/blob/main/Lib/fontTools/fontBuilder.py
"""
from absl import app
from absl import flags
from absl import logging
from base64 import b64encode
from fontTools.ttLib.ttFont import TTFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables._c_m_a_p import cmap_classes
import os
import pathlib
import shutil
import subprocess
import tempfile


FLAGS = flags.FLAGS


flags.DEFINE_boolean(
    "support_composite", False, "Whether to support composite tofu glyph (if False, will use the first glyph with paint)."
)
flags.DEFINE_string(
    "tofu_source_svg", "tofu.svg", "Filename of the SVG in tofu source dir to use in the Tofu font."
)
flags.DEFINE_integer(
    "version_major", None, "Major version number for the Tofu font."
)
flags.DEFINE_integer(
    "version_minor", None, "Minor version number for the Tofu font."
)
flags.DEFINE_integer(
    "ascender", None, "Ascender height."
)
flags.DEFINE_integer(
    "descender", None, "Descender height."
)
flags.DEFINE_integer(
    "line_gap", None, "Line gap."
)
flags.DEFINE_integer(
    "units_per_em", None, "Units per em."
)
flags.DEFINE_integer(
    "width", None, "Character width."
)


FAMILY_NAME = "Tofu"
FONT_FILENAME = "tofu.ttf"
TOFU_SOURCE_DIR = "source"
GLYPH_NAME = 'tofu'


def _script_path() -> pathlib.Path:
    return pathlib.Path(__file__).parent


def _tofu_source_svg_path() -> pathlib.Path:
    return _script_path() / TOFU_SOURCE_DIR / FLAGS.tofu_source_svg


def _compile_font(tofu_svg_path: pathlib.Path) -> pathlib.Path:
    """
    Compiles the Tofu font with nanoemoji.

    :returns: path to TTF file output
    """
    cmd = [
        'nanoemoji',
        '--family={}'.format(FAMILY_NAME),
        '--output_file={}'.format(FONT_FILENAME),
        '--color_format=glyf',
    ]
    if FLAGS.version_major:
        cmd.append('--version_major={}'.format(FLAGS.version_major))
    if FLAGS.version_minor:
        cmd.append('--version_minor={}'.format(FLAGS.version_minor))
    if FLAGS.ascender:
        cmd.append('--ascender={}'.format(FLAGS.ascender))
    if FLAGS.descender:
        cmd.append('--descender={}'.format(FLAGS.descender))
    if FLAGS.line_gap:
        cmd.append('--linegap={}'.format(FLAGS.line_gap))
    if FLAGS.units_per_em:
        cmd.append('--upem={}'.format(FLAGS.units_per_em))
    if FLAGS.width:
        cmd.append('--width={}'.format(FLAGS.width))

    cmd.append('{}'.format(tofu_svg_path))
    subprocess.run(cmd)

    return pathlib.Path.cwd() / 'build' / FONT_FILENAME


def _build_ttf() -> pathlib.Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        # Copy tofu source SVG to tmp dir with filename expected by nanoemoji
        tofu_svg_path = pathlib.Path.cwd() / '0000.svg'
        shutil.copyfile(_tofu_source_svg_path(), tofu_svg_path)
        ttf_file_path = _compile_font(tofu_svg_path)

        with TTFont(ttf_file_path) as font:
            fb = FontBuilder(font=font)
            if FLAGS.support_composite:
                glyph_order = [n for n in font.getGlyphNames() if n != 'space']
                glyphs = {n: fb.font['glyf'][n] for n in glyph_order}
                horizontal_metrics = {n: fb.font['hmtx'][n] for n in glyph_order}
                glyphs['.notdef'] = TTGlyphPen(None).glyph()
                glyphs[GLYPH_NAME] = glyphs[glyph_order[-1]]
                del glyphs[glyph_order[-1]]
                horizontal_metrics[GLYPH_NAME] = horizontal_metrics[glyph_order[-1]]
                del horizontal_metrics[glyph_order[-1]]
                glyph_order[-1] = GLYPH_NAME
            else:
                glyph_order = ['.notdef', GLYPH_NAME]
                for n in font.getGlyphNames():
                    if n == '.notdef':
                        continue
                    glyph = fb.font['glyf'][n]
                    if glyph.numberOfContours:
                        break
                glyphs = {
                    '.notdef': TTGlyphPen(None).glyph(),
                    GLYPH_NAME: glyph,
                }
                horizontal_metrics = {
                    '.notdef': fb.font['hmtx']['.notdef'],
                    GLYPH_NAME: fb.font['hmtx'][n],
                }

            fb.setupGlyf(glyphs)
            fb.setupGlyphOrder(glyph_order)
            fb.setupHorizontalMetrics(horizontal_metrics)

            # OTS is unhappy if we *only* have format 13
            fb.setupCharacterMap({1: GLYPH_NAME})

            # format 13: many to one
            # https://docs.microsoft.com/en-us/typography/opentype/spec/cmap#format-13-many-to-one-range-mappings
            # spec: subtable format 13 should only be used under platform ID 0 and encoding ID 6.
            # https://github.com/behdad/tofudetector/blob/master/tofu.ttx uses 3/10 and that seems to work.
            cmap_many_to_one = cmap_classes[13](13)
            cmap_many_to_one.platformID = 3
            cmap_many_to_one.platEncID = 10
            cmap_many_to_one.language = 0
            cmap_many_to_one.cmap = {cp: GLYPH_NAME for cp in range(
                0x10FFFF + 1) if cp > 1 and cp != 0xFE0F}

            fb.font['cmap'].tables.append(cmap_many_to_one)

            fb.setupPost(keepGlyphNames=True)

            ttf_file_path = _script_path() / FONT_FILENAME
            fb.save(ttf_file_path)

            return ttf_file_path


def _create_css(ttf_file_path: pathlib.Path):
    """Create the stylesheet with inlined font data."""
    css_file_path = ttf_file_path.parent / (ttf_file_path.stem + '.css')
    with open(ttf_file_path, mode='rb') as ttf_file:
        with open(css_file_path, mode='w') as css_file:
            content = '@font-face {{\n' \
                '  font-family: Tofu;\n' \
                '  src: url("data:font/ttf;base64,{ttf_data}");\n' \
                '}}\n'.format(ttf_data=b64encode(
                    ttf_file.read()).decode('utf-8'))
            css_file.write(content)


def _run(argv):
    ttf_file_path = _build_ttf()
    _create_css(ttf_file_path)


def main():
    app.run(_run)


if __name__ == '__main__':
    main()
