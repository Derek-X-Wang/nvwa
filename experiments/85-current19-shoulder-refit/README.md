# Current19 shoulder rest-refit

**Actual outcome: baseline PASS; one authoring attempt REJECT, zero assets.**
See [results and limits](RESULTS.md).

New `current19-native-production-v1` cohort: eighteen actual legacy recipes and
one separately opened v2 rear-arm2 Work, captured by one native producer/process.
The complete new baseline passed source reconstruction and an independent
nineteen-case audit. See [the measured baseline](evidence/baseline-v2.json).
Historical experiment84 authentication and its rejected hybrid corpus are frozen.

`current19.py` defines fail-closed collection/identity controls. Structural tests
use synthetic records and provide no actual geometry or quality evidence.
Capture, independent all-row reconstruction, one-candidate authoring and scoring
require parent stage approval and frozen provenance. Raw outputs live outside Git.

The capture path first retains all19 structurally valid samples plus completion.
It then audits geometry on every slot and aggregates failures. Exact20 ordered raw
files, completion semantics and gzip/raw byte equality are checked again through
the same stream admission path. Producer stdout/EOF/process wait has a600-second
deadline and owned-process cleanup. Geometry has a separate900-second cooperative
budget, checked before each case. It does not interrupt a running case. Remaining
slots become NOT-RUN and the cohort rejects if the budget expires between cases.

The first complete capture remains rejected: a dictionary-axis lookup in the
additional binary64 audit raised a TypeError. Its raw data and source capsule are
retained. After a source-grounded repair, a new capture passed all nineteen cases
without changing the binary, arithmetic limits, or historical checks. Lifecycle
controls execute real small Python subprocesses with short test deadlines.

The 284-file capture closure is separate from the prospective author/scorer
closure. A new author module cannot retroactively become an input of a capture.
The original reference policy supplies geometry rules only; its historical cohort
identity does not describe these new records. Any candidate would have its own
identity; this attempt created no asset.

From the repository root, run the portable controls in both Python modes:

```sh
python3 -B scripts/check-portable.py current19-shoulder-refit
```

The actual producer was built on an Apple Silicon Mac with the pinned toolchain:

```sh
CARGO_BUILD_JOBS=1 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0 \
  cargo build --locked --offline \
  --manifest-path experiments/85-current19-shoulder-refit/replay/Cargo.toml \
  --bin nvwa-current19-replay --target aarch64-apple-darwin
```

`capture.py --help`, `author.py --help`, and `evaluate.py --help` describe the
actual interfaces. They require completed build, capture, and stage receipts;
synthetic control results cannot replace those receipts. Authoring reserves one
fixed output directory before computing planes. It does not retry after a failed
attempt. Scoring requires all nineteen baseline checks before candidate reads.

The original eighteen historical raw arrays are still missing. Their exact gates
remain unchanged; the new baseline is not recovered historical evidence.
GPU, candidate shading/upload parity, Web A/B, CLI candidate exchange, and visual
adoption remain unverified until their own conditional stages pass.
