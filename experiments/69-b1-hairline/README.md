#69 — one hairline mip candidate, stopped at CPU rejection

**REJECT this candidate; visual quality remains HOLD.** A single proposed
coverage-preserving mip chain failed its predeclared global-alpha engineering
condition before rendering. There is no 69 candidate screenshot, native/Web
comparison, performance measurement or production change.

This differs from 65's hair alpha-to-coverage toggle: it evaluates spatial
averaging and a finite global alpha correction family for the existing texture.
The source decode path (`crates/nvwa-runtime/src/appearance/assets.rs`, `decode`)
uses `Image::from_buffer` with the default sampler and does not generate a mip
chain there. The cached Bevy 0.19.1 PNG conversion initializes one mip level.
This is source inspection, not an observed GPU image descriptor. Texture
minification is a hypothesis; no cause of the visible hairline is confirmed.

From the repository root, with Python 3 and no additional packages:

```sh
python3 -B experiments/69-b1-hairline/check_alpha.py --output /tmp/hairline69-alpha.json
python3 -B -m unittest discover -s experiments/69-b1-hairline -p test_alpha.py -v
python3 -O -B -m unittest discover -s experiments/69-b1-hairline -p test_alpha.py -v
```

The first command must exit **1**, print `CPU_REJECTED` with failed level 1,
and produce bytes identical to `alpha-reference.json`. Exit 2 means an input or
execution error. An optional `--source PATH` accepts only the exact authenticated
PNG documented in `PROVENANCE.json`; no download is performed. The decoder is
limited to this approved RGBA8 input, not a general untrusted-image service.
The tests use small hand controls and enumerate all finite scales independently
from the retained histograms. They do not render or establish local quality.

See `POLICY.md` for the frozen definition, `RESULTS.md` for actual counts,
`validation.json` for executed checks, and `REPLACEMENT-REQUIREMENTS.md` for
source limits and a bounded later asset review. No source assets are copied
into this experiment. Existing licensed assets remain in their original path.

The ignored `.private-runtime/` archive preserves unfinished/uncompiled work
and a SHA inventory. It is intentionally excluded from publication. A later
experiment 68 dual-end baseline, if captured, is separate evidence and cannot
be described as a 69 candidate render.
