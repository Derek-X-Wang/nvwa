# Bundled Chinese fallback

`NvwaSansSC-Regular.ttf` is a static weight-400 derivative of the pinned official
Noto Sans SC variable TTF. It retains the original regional source's complete
character map and glyph order. No additional character subset is applied.
`PROVENANCE.json` records source commits, URLs, hashes, and the reproducible
fontTools derivation. Python/fontTools are not needed by the application.

The native and Web builds embed the same font bytes in egui. The font is appended
to the existing proportional and monospace fallback chains, preserving default
Latin and symbol fonts. A CJK fallback in the monospace chain does not guarantee
equal-width Latin and Chinese glyphs.

Coverage includes 30,890 mapped Unicode codepoints and 31,036 glyphs, with broad
Simplified and Traditional Chinese character support and Simplified Chinese
regional glyph forms. This font does not cover every Chinese filename:

- Basic Han U+4E00–9FFF: 20,976 mappings; U+9FF0–9FFF absent.
- Extension A U+3400–4DBF: 6,582 mappings; U+4DB6–4DBF absent.
- CJK punctuation U+3000–303F: all 64 slots mapped.
- Most supplementary Han characters, including `𠀀` and `𠮷`, are absent.
- Hangul syllables are absent. Traditional, Japanese, and Korean typography are
  not guaranteed by this Simplified Chinese regional font.

Raw font size is 10,595,928 bytes; standalone gzip level 9 is 6,303,513 bytes.
These are font-only measurements, not the final application or Wasm payload.
Detailed mapped and missing ranges are in `experiments/06-cjk-fonts/measurements.json`.

Distribute `OFL.txt` and `NOTICE.md` with the font/application, including Web
packaging. The font and derivative remain under SIL OFL 1.1. `Source` is a reserved
font name; the derivative is explicitly named Nvwa Sans SC Regular. The application
license is separate from the font license.
