# Genuine sample admission: HOLD

This report-only experiment reproduces the numerical reasons to hold playable
admission of the exact genuine 90-frame sample from experiment 44. It does not
normalize, export, play, or fix that sample.

See [REPORT.md](REPORT.md) for root rebasing, failed mapping controls, unresolved
semantic/rest bases, source references, and the precise evidence boundary.

From the repository root, with Python 3.9+ and no dependencies:

```sh
python3 -B experiments/45-genuine-rig-admission/probe.py
python3 -B experiments/45-genuine-rig-admission/test_controls.py
```

JSON goes to stdout. Optional `--out new-file.json` requires an existing parent
directory and refuses existing different bytes. All current inputs are pinned
public files. Historical originals have private paths and are retained solely
for attribution and unchanged-evidence comparison.

Historical floats use absolute and relative tolerances of `1e-13`; structure,
types, counts, identities, and file hashes stay exact. Nonfinite floats are
rejected. Actual results can differ in the last bits across Python runtimes;
use a fresh output path. See `portability.json` for the original Python 3.9
failure and restored checks under 3.9.6, 3.12.11, and 3.14.7.

VERIFIED — Probe and 31 rejection controls pass on all three tested runtimes.
NOT-RUN — Normalization, export, playback, semantic or contact acceptance.
