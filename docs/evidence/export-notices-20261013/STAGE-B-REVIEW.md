# R2 targeted re-review — stage B

**ACCEPT stage B. Findings 1 and 2 are resolved for the explicit frozen-cohort integrity contract.** No new material finding. Combined with stage A, all three original R2 findings are resolved. This does not approve redistribution, close issues 5/10, or review the still-moving final checkpoint/publication packet; stage C remains outstanding.

## Trust and scope

The new independent anchor is not chosen by the candidate. `cohort.py` pins `ab92b4816b18191e0d24d063e43a9e183cd3204114a4321da5d478455a403bf2`, exactly the original manifest hash already recorded and factually verified by this independent reviewer before rework. I verified the new external anchor's bytes against that original receipt. Indexed reads use that fixed inventory. Candidate manifest fields, including provenance, source comparisons, payload inventories, gaps and owner policy, must match the independently fixed capture.

This design intentionally checks only this captured production cohort; it is not a generic license policy engine or proof that a newly generated manifest is factually correct. A different production cohort needs explicit new audit and a reviewed anchor/code change. Changing checker code plus its pin is outside the documented trust boundary. That boundary is adequate and candid for this experiment.

The added semantic joins agree with the preserved facts: exact 32-source inventory and retained build hashes; package manifests/source/provenance; local/public supplement repository and VCS-commit joins; original notice hashes and copyright lines; notice-only versus license-text candidates; three distinct asset records/four default-font records; font and fixture provenance; all 45 gap records and root owner UNKNOWN. No mutable candidate field can authorize its own replacement anchor.

## Independent execution

VERIFIED — 93 fresh checker invocations: 18 original controls, 66 v2 controls, eight independent boundary checks and one actual live-source baseline. Every expected red and restored green passed. All seven original false-green counterexamples now fail on copied production candidates. The broader family rejects altered source paths/hashes, duplicate records, notice/source manifests, author/copyright fields, supplemental URL/repository/coverage, asset/font payloads and references, target metadata, removed inputs, unknown fields, and self-consistent edits to mutable retained-input/package-metadata anchors.

Independent boundary checks rejected: a changed external anchor; an unindexed added file; unavailable live source inputs; and a newly present root LICENSE. Exact restorations passed. Portable checking from an unrelated empty working directory passed and reports `live_source_check: NOT-RUN`. Live checking rehashed the actual 32 sources and passed as VERIFIED; missing sources fail rather than masquerading as verified or absent. Default-font payload bytes and remote source availability remain retained observations, as documented; the portable check does not claim fresh cache/network reads.

The new collector ran locked/offline and reproduced the original candidate manifest byte-for-byte at `ab92b481…`: 323 resolver-input packages, 1039 indexed files, 307 native/278 Web package sets, 21 missing-text packages, three first-party unknown licenses and 45 gaps. The explicit root-license guard and exact-frozen-capture comparison are present; no new license was selected.

## Preservation and limits

All 1040 original candidate files (manifest plus 1039 indexed files) match my pre-rework hashes. All 50 files in baseline-v1 match both their preservation receipt and my independent original snapshot; all 43 original evidence files remain unchanged. All 1380 experiment-36 files present at stage-B intake remained unchanged by this reviewer. Exact source hashes are in `postrun-reconciliation.json`; raw controls and reproduction outputs are retained under this stage-b directory.

No new network request, Rust build, browser, UI, GPU, download, signing, notarization, clean-machine test, Git/GitHub write or legal approval. The candidate remains PARTIAL/BLOCKED and owner licensing remains UNKNOWN. New cohort acceptance and final binary membership are not inferred. Final root checkpoint/CI/publication documents are excluded from this stage.

All mutation/checker-bundle/source-root copies created for boundary tests were removed after retaining outputs. Original/v2 control scratch directories are empty. Reproduction output and receipts remain private for root. All finite subprocesses completed and were reaped; no reviewer-owned persistent processes. **QUIESCENT**.
