# Fixture calibration candidate

This experiment implements the root-selected **physical identity** policy for
the exact existing SOMA30 sample and Nvwa18 fixture. Independent calibration
review is pending. No normalized clip, generated Work, exporter or player is
produced here.

From the repository root, Python 3.9+ and the standard library only:

```sh
python3 -B experiments/47-fixture-rig-calibration/calibrate.py
python3 -B experiments/47-fixture-rig-calibration/test_controls.py
python3 -B -O experiments/47-fixture-rig-calibration/test_controls.py
```

Commands emit JSON on stdout. `candidates.json` retains both the selected
physical policy and rejected named-label reflection. `calibration.json` is the
selected candidate's complete machine-readable policy and per-joint frames;
its status remains `PROPOSED_NOT_ADMITTED`. `verification.json` retains the
actual controls. The tests reproduce both files with strict types, shapes,
identities and finite float leaves (`1e-13` absolute/relative tolerance).

The [report](REPORT.md) explains the mapping, conventions, independent
expectations, measured export precision and gates. The independently derived
[reference capsule](reference/) owns the original-source authority audit.

VERIFIED — All 90 genuine frames, exact affine markers, 89 positive and43
rejection checks pass on Python3.9.6 and3.14.7, normal and `-O`.
NOT-RUN — Independent calibration admission, normalized output, generated
Work, native/Web playback, runtime decoder parity and new inference.
