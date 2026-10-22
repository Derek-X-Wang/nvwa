# Offline garment witness attribution (#112)

This experiment compares three existing same-pose captures. It does not generate
a character frame, modify a test, change a gate, download inputs or start CI.
See [CONTRACT.md](CONTRACT.md) for the frozen identities and no-touch boundary.

## Inputs

Use the already retained experiment60 Linux frame and the two experiment85
current19 Mac frames. All three selected filenames are
`t+1__b1_arm_rehearsal_v1__k16.json.gz`. Their locations and producer schemas
differ. The analyzer validates each through its existing source seam and records
hashes rather than relabeling one schema as the other.

The repository's existing B1 raw assets and source analyzers must be present.
Use an existing Python 3.12+ interpreter; no new packages or assets are required.
This command reads its inputs and requires a new output filename:

```sh
python3 -B experiments/87-linux-witness-drift/analyze.py \
  --linux /absolute/path/to/linux-matrix/keyframes/t+1__b1_arm_rehearsal_v1__k16.json.gz \
  --mac-v1 /absolute/path/to/current19-baseline-v1 \
  --mac-v2 /absolute/path/to/current19-baseline-v2 \
  --out /absolute/path/to/new-offline-comparison.json
```

The output distinguishes the original scalar assertion, full source validation,
captured-array comparisons, and offline component swaps. A reconstructed or
swapped frame is an analysis probe, never a new runtime capture.

`--linux` takes a single frame. The Mac arguments take capture directories with
their existing `manifest.json`, identity receipt and selected `keyframes/` file.
Run the real-frame controls with the same existing inputs:

```sh
python3 -B experiments/87-linux-witness-drift/test_analyze.py \
  --linux /absolute/path/to/linux-matrix/keyframes/t+1__b1_arm_rehearsal_v1__k16.json.gz \
  --mac-v1 /absolute/path/to/current19-baseline-v1
```

## Original failure signal

The unchanged normal control can be replayed on the retained Linux frame:

```sh
python3 -B experiments/70-b1-garment-defect/test_controls.py \
  --asset-root assets/characters/mpfb-b1-v1 \
  --frame /absolute/path/to/linux-matrix/keyframes/t+1__b1_arm_rehearsal_v1__k16.json.gz
```

It exits 1 with two of 18 original assertions failing. Keeping that red signal is
part of this diagnosis; the new analysis does not claim to fix it. The original
Linux optimized control remains NOT-RUN. No offline result changes the failed
pilot conclusion or adopts a runner migration.
