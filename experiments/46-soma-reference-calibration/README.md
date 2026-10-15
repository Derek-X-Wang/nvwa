# SOMA30 reference calibration diagnostics

**Anatomical semantics and target playable admission remain HOLD.** This offline
report tests signed reference constraints, geometric frame observability and a
conditional pelvis-world equation on the exact retained 90-frame sample.

From the repository root, with Python 3.9+ and standard library only:

```sh
python3 -B experiments/46-soma-reference-calibration/calibrate.py
python3 -B experiments/46-soma-reference-calibration/test_controls.py
```

Both commands emit structured JSON on stdout. The analyzer has no output-file
option. `results.json` and `verification.json` retain actual invocations.
Floating metrics may vary in their last bits between runtimes. The control
comparator accepts only finite float leaves with absolute/relative tolerance
`1e-13`; types, counts, shapes, identities and input hashes remain exact.

See [REPORT.md](REPORT.md) for assumptions, results and limits. The
[development record](development-history/README.md) retains observed failures,
repairs and six final normal/optimized portability runs.

VERIFIED — 27 positive and 48 rejection checks pass on Python 3.9.23, 3.12.11
and 3.14.7, with and without `-O`; all ten public input pins stay exact.
NOT-RUN — Anatomical admission, pose transfer adoption, normalized motion,
export, generated Work, native/Web playback, new inference or scale/contact fit.
