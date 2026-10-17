# Rejected local garment corrections

Issue [80](https://github.com/Derek-X-Wang/nvwa/issues/80), one fixed A/B cycle on continuous-motion candidate `c655217c0c9c41069b0f45a0d8c2795e455ca6bf`. **Neither candidate is adopted.** Same B1 body, sportsuit and actual retained bone/rest samples; no new assets, downloads or model runs.

| Fixed method | Target arm triangle at torso+1/2s | Recorded local regression | Decision |
| --- | --- | --- | --- |
| A, one local weight smoothing pass | Area/rest ratio22.0056→19.5718; rest unchanged | Mixed boundary-face maximum area ratio5.31541→5.54543; six arm-frame regressions | REJECT/HOLD |
| B, local original-offset retention | Ratio against its own rest22.0056→4.0111; absolute posed area worsens ~0.77%; gain is mostly denominator growth | Non-core incident-face maximum candidate-rest ratio5.31541→5.69741 | REJECT/HOLD |

Both cover the same16 source vertices and all52 incident triangles, including34 mixed affected/exterior faces. The A boundary and B non-core groups reported above are explicitly different subsets (34mixed faces versus35non-core faces); their labels are not interchangeable. There are separately34crossing edges. The30 retained actual BASELINE captures cover3 torso recipes, jaw0, two authored actions and0/1/2/3/4s. Candidate deformation is an offline f64 replay from those actual bones/rest, not new compiled runtime or GPU proof. Each method preserves exterior coordinates, original source assets, body/rig, all positive influence semantics and old foot/root gates. Values and limits are in [A](weights/README.md) and [B](rest-fit/report.md); the fixed [contract](CONTRACT.md) retains review clarifications and the ordering of preliminary observations.

## Reproduce

Use Python stdlib; existing experiment60 modules are the only imports. In this exact branch, generate original actual keyframes using [experiment60](../60-b1-continuous-motion/README.md), or use the retained r4 keyframe directory. Each output directory must be new. No altered candidate is loaded by the product.

```sh
python3 -B experiments/61-b1-garment-ab/weights/run.py --captures "$CAPTURES" --output "$NEW_A_OUTPUT"
python3 -B experiments/61-b1-garment-ab/rest-fit/compare.py --captures "$CAPTURES" --output "$NEW_B_OUTPUT"
python3 -B experiments/61-b1-garment-ab/weights/test_controls.py
python3 -B -O experiments/61-b1-garment-ab/weights/test_controls.py
python3 -B experiments/61-b1-garment-ab/rest-fit/test_controls.py
python3 -B -O experiments/61-b1-garment-ab/rest-fit/test_controls.py
```

Baseline raw geometry stays in task-owned output, not in this branch as hundreds of megabytes. A compact source/capture hash index and results are retained; full30-frame details and absolute geometry remain in the task outputs. This branch is the throwaway primary source, not a production fix.

## Why no graphical build followed

Both candidates violated the conservative numerical no-regression condition. Root stopped before implementing/compiling the planned temporary renderer. The four unused root-owned Cargo/source placeholders were removed after exact-byte checks; no test, failure, product guard or requirement was deleted to obtain success. The graphic contract remains a record of what a future eligible candidate would require, not an executed capability. No new Rust/native/Web build, altered runtime upload/readback or candidate screenshot is claimed. Existing normal-product Web/CI evidence belongs to PR81 and is separate.

Eight cheap comparator controls pass in normal and optimized Python (5A+3B,16 executions). Independent review/replay is recorded in the decision receipt when complete. General cloth collision, physical penetration, self-intersection, full jaw-grid/intermediate actual sampling, native/Web candidate visualization and production admission are **NOT-RUN**. Nearest-face signs and fold/strain counts remain descriptors. Both recipes stay frozen; no parameter sweep followed rejection.

The result narrows the next useful work: a source-authoritative reference body/helper correspondence before another rest-fit change, or a deformation-aware local correction with boundary constraints before another weighting change. Neither is automatically authorized as an unlimited new cycle. Garment/M2 quality remains HOLD; #3 stays blocked and #4 retains measurement gaps. This failed experiment does not add a new dependency to appearance#79 after motion#78 is accepted.
