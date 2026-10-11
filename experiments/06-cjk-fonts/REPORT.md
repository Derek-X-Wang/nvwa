# 06 — Licensed bundled CJK font comparison

## Outcome and finite decision

**GO for an integration candidate: full-cmap static regular 400.**
The derived `NvwaSansSC-Regular.ttf` preserves every cmap subtable's semantics,
including Unicode variation sequences, and all 31,036 source glyphs. It reduces
raw font bytes by 7,176,372 (40.38%) and standalone gzip bytes by 4,973,050 (44.10%).
It is a broad Chinese fallback rather than a subset of the demonstration text.
No additional character subset is applied. The source is already a regional
Simplified Chinese subset of the Noto CJK family.

**NO-GO for claiming native/Web readiness or release approval from this spike.**
No compiler, Cargo, GPU, desktop application, browser, or server was run.
Actual Nvwa native/Web rendering, startup cost, memory, bundle sizes, font atlas
growth, and visual quality are NOT-RUN. A parsed cmap establishes mappings, not
successful rendering, correct glyph appearance, or universal Chinese coverage.

Only `experiments/06-cjk-fonts/` and `.work/cjk-fonts/` were written. Main source,
main assets, manifests, lockfile, and project scripts were not changed.

## A/B measurements

Measured using installed Python 3.9.5 and fontTools 4.60.2 on the local Mac.
Compression is Python `gzip.compress(data, compresslevel=9, mtime=0)` over each
font alone. These figures do not predict the final executable or compressed Wasm
size; surrounding bytes, the build, and the hosting compression change those.

| Candidate | Raw bytes | Raw MiB | gzip level 9 bytes | gzip MiB | Mapped Unicode points | Glyphs |
|---|---:|---:|---:|---:|---:|---:|
| Original full variable Noto Sans SC | 17,772,300 | 16.949 | 11,276,563 | 10.754 | 30,890 | 31,036 |
| Full-cmap static regular 400 derivative | 10,595,928 | 10.105 | 6,303,513 | 6.011 | 30,890 | 31,036 |

The variable font has one `wght` axis, range 100–900, **default 100**. Embedding it
without overriding the axis selects Thin, rather than Regular. The static font
has OS/2 weight class 400 and no variation tables/axes. fontTools runs during the
reproducible derivation only; applications consume an ordinary TTF and do not
need Python, fontTools, a network connection, or a system font.

Candidate artifact: `.work/cjk-fonts/candidates/NvwaSansSC-Regular.ttf`.
Its SHA-256 is
`902150f57c7bdd221323aad3697d0f78edd015a5fe1af39675e918a8959d51ea`.

## Provenance and distribution license

Google Fonts source is pinned to commit
`a85815a42757630ce188fdad368c2dfc444d4773`.
The original TTF SHA-256 is
`a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da`.
Primary sources:

- [Pinned Google Fonts TTF](https://raw.githubusercontent.com/google/fonts/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf)
- [Pinned family metadata](https://raw.githubusercontent.com/google/fonts/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/METADATA.pb)
- [Pinned copyright and OFL](https://raw.githubusercontent.com/google/fonts/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/OFL.txt)

The metadata points to notofonts/noto-cjk commit
`523d033d6cb47f4a80c58a35753646f5c3608a78`. The official source TTF was also
downloaded and measured: 17,773,132 bytes; SHA-256
`d68bafcb48a2707749396aa12bbbd833cb70401f3a9a689fd2902c7e0d295964`.
It has identical cmap semantics and glyph order to the Google Fonts source.
The binaries differ by 832 bytes in size. That does not establish identical
outline tables or a particular upstream postprocessing history.

- [Pinned Noto CJK source TTF](https://raw.githubusercontent.com/notofonts/noto-cjk/523d033d6cb47f4a80c58a35753646f5c3608a78/Sans/Variable/TTF/Subset/NotoSansSC-VF.ttf)
- [Pinned Noto CJK license](https://raw.githubusercontent.com/notofonts/noto-cjk/523d033d6cb47f4a80c58a35753646f5c3608a78/LICENSE)

The original is SIL OFL 1.1, with copyright 2014–2021 Adobe and Reserved Font Name
`Source`. OFL permits font embedding, modification, and redistribution with
software subject to its conditions. Distribution must include the copyright
notice and license; the font remains under OFL and cannot be sold by itself.
Modified versions must respect reserved primary names and must not imply author
endorsement. The derivative is explicitly named **Nvwa Sans SC Regular**.
Copyright and OFL name records are preserved. Ship the copied `OFL.txt` and
`NOTICE.md` with any selected font artifact, including the Web distribution.
[Owning license and conditions](https://raw.githubusercontent.com/google/fonts/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/OFL.txt)

No proprietary system font was bundled. No paid service, installation, model
weight download, Git operation, or external write was performed.

## Actual coverage and limits

All values below count **Unicode block slots**, including unassigned slots;
they are not percentages of language usage or a GB18030 compliance claim.
Block boundaries match [Unicode 17 Blocks.txt](https://www.unicode.org/Public/17.0.0/ucd/Blocks.txt).
Detailed missing ranges, every supported range, cmap subtable counts, names,
hashes, and sample strings are recorded in `measurements.json`.

| Range | Mapped / block slots | Limit |
|---|---:|---|
| Printable ASCII U+0020–007E | 95 / 95 | Complete for this range |
| CJK punctuation U+3000–303F | 64 / 64 | Complete for this range |
| CJK Unified Ideographs U+4E00–9FFF | 20,976 / 20,992 | U+9FF0–9FFF missing |
| Extension A U+3400–4DBF | 6,582 / 6,592 | U+4DB6–4DBF missing |
| CJK Compatibility Ideographs U+F900–FAFF | 122 / 512 | Partial; see JSON ranges |
| Halfwidth/Fullwidth Forms U+FF00–FFEF | 224 / 240 | Partial; see JSON ranges |
| Extension B | 54 / 42,720 | Most characters unsupported |
| Extension C | 44 / 4,160 | Most characters unsupported |
| Extension D | 8 / 224 | Most characters unsupported |
| Extension E | 108 / 5,776 | Most characters unsupported |
| Extension F | 1 / 7,488 | Most characters unsupported |
| Extension G | 3 / 4,944 | Most characters unsupported |
| Extensions H, I, J | 0 / 9,120 combined | Unsupported |
| Compatibility supplement | 2 / 544 | Most characters unsupported |
| Bopomofo | 43 / 48 | Partial |
| Bopomofo Extended | 28 / 32 | U+31BC–31BF missing |
| Hiragana | 93 / 96 | Some missing/unassigned slots |
| Katakana | 96 / 96 | Complete for this range |
| Hangul syllables | 0 / 11,184 | Unsupported |

Simplified UI and Chinese filename corpus: **all unique codepoints mapped**.
Traditional Chinese filename corpus: **all unique codepoints mapped**. These
include characters such as 女娲/女媧, 臺灣, 廣東話, 龜, 鬱, and Chinese brackets.
The full source mapping is the coverage guarantee, not this finite sample set.
Traditional characters use the source font's regional glyph forms; this spike
does not establish Traditional Chinese typography or full Japanese/Korean support.

The mixed filename/symbol sample is missing `✗` U+2717 in this font. Existing egui
fallbacks may cover it, but that combined-chain result is NOT-RUN. Rare-character
probes reveal missing `𠀀` U+20000 and `𠮷` U+20BB7, while some other supplementary
characters are present. Appending this font cannot guarantee arbitrary Unicode
filenames. There are two variation-selector records in cmap format 14; these
are preserved exactly. No claim is made about all ideographic variation sequences.

## Exact egui integration contract, source inspected

The local lockfile uses **bevy_egui 0.42.0, egui 0.36.2, epaint 0.36.2**.
Contrary to the initial dispatch assumption, `ab_glyph` is absent from the lock;
this epaint version uses skrifa font parsing/outlines and harfrust shaping.
The installed exact sources were read directly; no version was guessed:

- `~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/epaint-0.36.2/src/text/fonts.rs:112–136`: `FontData::from_static(&'static [u8])` accepts TTF/OTF data, with face index 0.
- The same file, lines 400–448: `FontDefinitions::default()`, `font_data: BTreeMap<String, Arc<FontData>>`, and ordered font-family fallback vectors.
- `epaint-0.36.2/src/text/font.rs:387–426`: skrifa parsing and harfrust shaper construction.
- `egui-0.36.2/src/context.rs:2100–2120`: `Context::set_fonts`, active at the next pass.

Proposed integration, **not compiled or installed by this spike**:

```rust
let mut fonts = egui::FontDefinitions::default();
let name = "nvwa-cjk".to_owned();
fonts.font_data.insert(
    name.clone(),
    std::sync::Arc::new(egui::FontData::from_static(include_bytes!(
        "<selected bundled font asset>"
    ))),
);
for family in [egui::FontFamily::Proportional, egui::FontFamily::Monospace] {
    fonts.families.entry(family).or_default().push(name.clone());
}
egui_context.set_fonts(fonts);
```

Append to both default families to preserve current Latin text and symbols while
adding Chinese fallback. Use the same embedded bytes and configuration in the
shared native/Web startup path. Configure each actual egui context once; allow
the next pass to install fonts before judging text. The source CJK font is
proportional; fallback through the Monospace family does not make every CJK glyph
equal-width with the Latin monospace font.

## Reproduction and acceptance

The existing installed fontTools version is required for byte reproducibility.
The script does not install anything. The exact official source/license hashes
and derivative hash are hard-pinned. Cached source tampering and a changed static
output fail. The head timestamp is preserved. Name records are changed explicitly
to identify the derivative while copyright/license records are preserved.

From repository root:

```sh
# First run only, if the pinned upstream files are absent:
PYTHONDONTWRITEBYTECODE=1 python3 experiments/06-cjk-fonts/compare_fonts.py --download

# Offline, repeat full derivation and assert identical derivative bytes:
PYTHONDONTWRITEBYTECODE=1 python3 experiments/06-cjk-fonts/compare_fonts.py --rebuild

# Offline, validate pinned sources/candidate and refresh measurements:
PYTHONDONTWRITEBYTECODE=1 python3 experiments/06-cjk-fonts/compare_fonts.py
```

CPU acceptance for a candidate is finite: valid pinned source bytes; identical
full cmap semantics and glyph order across original, upstream, and derivative;
static weight 400 with variable tables removed; copyright/OFL records retained;
printable ASCII and both Chinese UI/filename samples mapped; raw font below
11 MiB and gzip below 7 MiB. These payload ceilings bound this candidate choice;
they are experiment limits, not a measured product performance budget.

Runtime acceptance remains root-owned: actually observe both native and Web
Chinese text in the existing UI and opened/saved filenames, observe mixed Latin
and Chinese text in proportional/monospace widgets, preserve existing symbols,
and record startup/payload/memory concerns. Exit integration if either platform
fails parsing/rendering, glyphs are clipped or absent for supported sample text,
or actual payload/performance is unacceptable. Do not substitute a proprietary
font or reduce the candidate to a small demonstration-only character subset.

Artifacts: `compare_fonts.py`, `measurements.json`, `rebuild-output.txt`, copied
`OFL.txt`, derivative `NOTICE.md`, and this report. Source/candidate binaries remain
under `.work/cjk-fonts/`; promotion to shipped assets requires the root's next
stage assignment after PR17 merge.

VERIFIED — Pinned licensed TTFs parsed; static full-cmap derivation and byte/gzip coverage measured.
NOT-RUN — Native/Web rendering, application builds, packaging and performance.

## Mainline candidate integration after PR17 merge

The following bounded integration candidate is now present, without a claim that
graphics, compilation, or tests have run:

- `assets/fonts/` contains the static candidate, copied OFL, derivative notice,
  source provenance, and coverage limits. The shipped font's bytes match the
  recorded derivative SHA-256.
- `crates/nvwa-studio/src/fonts.rs` configures the default egui proportional and
  monospace families with an appended Chinese fallback. `FontData::from_static`
  borrows the embedded bytes; font definitions are configured for
  `Added<EguiContext>` only, rather than in a multipass UI function.
- The shared `build_app_for_mode` registers this system in `PreUpdate`, after
  `EguiPreUpdateSet::InitContexts` and before `EguiPreUpdateSet::BeginPass`. Both
  Studio and Player receive the same setup, including subsequently added contexts.
- The Studio file label reads `作品 / Work`, a real bilingual UI label.
- Two CPU tests are added for actual egui glyph availability/layout, unchanged
  default Latin glyph width, known unsupported supplementary Han, and installation
  for each newly added context without resetting existing contexts. They have
  **NOT-RUN** in this worker; the root owns Rust verification and graphics checks.

VERIFIED — Shipped font/license hashes match spike artifacts; scoped rustfmt completed.
NOT-RUN — Added Rust tests, native/Web builds, rendering, packaging and performance.

## Integrated acceptance checkpoint

**Adopt for the verified native/Web scope.** Root completed 59 workspace tests,
strict native/Wasm clippy, both release builds and actual Studio rendering. Both
formats visibly render `作品 / Work` and representative Chinese filenames. Real
Unicode GUI Save/Open retains the full revision6 document. Both output packages
contain exact OFL, NOTICE and provenance. No mainline dependency or lockfile changed.

Actual unique Web HTML/JS/Wasm/GLB gzip sum is 20,497,855 bytes versus the repaired
PR17 baseline 14,183,418: +6,314,437. Including the same demo work gives20,498,378.
This is file compression, not cold-network timing. Raw packaged native executable
is102,888,672 bytes, versus PR17's92,197,040. No separate font fetch is needed.

The two CPU test-harness repairs and independently accepted semantics are recorded
in [review](../../docs/evidence/input-fonts/REVIEW.md). The original failed logs
remain. The exact source/artifact snapshot is in
[manifest](../../docs/evidence/input-fonts/build-manifest.json); actual GUI details
and executable steps are in [acceptance](../../docs/evidence/input-fonts/ACCEPTANCE.md).

PARTIAL — Font rendering, Unicode save/reload, package notices, builds and size
measured. Real IME/physical clipboard/modifiers and native continuous drag/focus
remain unverified. Mac locked during remaining native inputs; new font-build
startup/cadence/GPU/browser-memory measurements are NOT-RUN. Previous M0/M1
performance numbers stay historical, rather than being attributed to this font build.
