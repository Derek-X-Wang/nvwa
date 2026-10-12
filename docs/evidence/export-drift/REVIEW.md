# Blender export investigation review

2026-10-12. Fresh independent Astra R2 reviewer, separate from the Sol export author. This is agent-authored review. Base main is `de4ddef`; root verified every one of the 28 protected files equals that base and the recorded before/after hashes.

The first review independently reran eleven tests, decoded actual GLB data and reproduced the retained comparison. It confirmed 33 JSON differences, 414 resolved usages, ten normal accessors/485 differing components, four changed eye index sequences with identical oriented triangle multisets, zero uncovered binary bytes, unchanged body indices, both fixture validations and profile metadata. It also confirmed the `.blend` block/address/payload counts and six installed exporter source hashes.

One P2 issue was found in the experiment CLI: `--require-exact` could return success for a byte-different but equivalently decoded GLB, or changes limited to `.blend`/source proof. The author changed the gate to require byte equality across all three artifacts and added actual-file CLI regressions. Original-red and explicit old-gate mutation-red/restored-green evidence is retained in [byte-gate-test-evidence.txt](../../../experiments/26-export-drift/byte-gate-test-evidence.txt).

Targeted R2 rereview accepted the fix with no remaining findings. It independently ran the complete **14-test suite**, zero skips, in 22.927 seconds; byte-only GLB, `.blend` and source-proof changes return exit 1, the actual pair returns 1 and self control returns 0. Fresh output exactly matches the current measurement snapshot. First-run and later-label reproduction paths, including `NVWA_EXPORT_TEST_PAIR`, are consistent. Protected hashes still match. The reviewer inspected retained mutation evidence; it did not repeat the mutation during read-only rereview.

Reviewed SHA-256:

| File | Hash |
| --- | --- |
| `compare.py` | `f6b2f1a32f381712b0d864aa2609fb5854a2e857763837404808a1cc7f751627` |
| `test_compare.py` | `395d5256198c5b2cdc7faf76412fb551bdb8d4f417c8e7c7b49d672184073d5a` |
| `run_pair.py` | `5d88e9d02fc2a05f5c2b2b5ff3a82e8922e843fc06a1cad674f6b6a1bec0c906` |
| `REPORT.md` | `0a8a95354e879201e3fd2ef1610e4194ae816246dd74e50dfda4a948664fb6f9` |
| `measurements.json` | `78bdc0e75aef40ef3c55f7406fba8937747675823bb954e55f1a14df9f76bc6c` |

Accepted for issue #7's precise bounded documentation alternative. Internal causes, future-run bounds, a determinism fix, complete `.blend` semantics, native/Web rendering and visual shading impact remain unproved. No source edits, Blender exports, Cargo builds or rendering were performed by the reviewer.

VERIFIED — Independent measurement checks, actual validators, 14 tests and repaired exact-byte gate. NOT-RUN — Rendering and full native-scene equivalence.
