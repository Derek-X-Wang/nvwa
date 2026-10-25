# Stage B independent code review

Verdict: PASS FOR ROOT HASH FREEZE AND ONE AUTHORIZED EXECUTION. Zero blocking findings. This review does not release execution; root remains the release authority. No actual88 candidate constructor or evaluator was invoked by the reviewer.

## Reviewed exact inputs

- candidate.py: `4a2744b7812cb3849ea86ae0d26b9321f98c9f5e51fd888413f3ffa2a6cab2dd`
- evaluate.py: `ce7b5465b8f0264b7174e8f979d0422cf99f582cdf10fa57e62e15d16b50fd6e`
- test_controls.py: `35ad6b028187d987f0022e5227af8c8b0b53dfcf93acdbcea63caa6645f1d1a1`
- PROPOSAL.md: `26a88b0a04fdf7248612a592def42b63086192d59a3504de872a187742894aeb`
- input-pins.json: `02dc61cc3ea3c9ced7fc917f6f6d0c3bbe151e71372c76e0a3855c2752b602db`
- README.md: `639779f4a7c862a9989c3fda8f5f01d5b92eb7b15a2795b1e510f4c1838e9c8f`

All6 hashes match author receipt; all19 source pins independently rechecked unchanged. Candidate asset and Work do not exist at review end. Readback: code-hash-readback.json.

## Scope and implementation evidence

`candidate.py:59–96,165–188` implements the frozen L=.5 /20mm field and derives eligibility from exact original positive support inside pinned96. Only42 arm rows pass,54 torso rows remain outside writes. Every old positive stays in its original slot; chest takes the first old zero slot; the remaining zero slot is retained, including negative-zero bits. The code performs direct binary32 storage without renormalization, sorting, merging or pruning. Positivity, finite nonnegative weights and2e-6 normalization are checked after serialization. The1% cap remains; zero discarded mass is justified by no removal and exact operation identity, not a substitute for support retention.

`candidate.py:127–162,191–234` places raw readback/exact-operation and forbidden-byte validation on the actual constructor path and again after GLB decode. Length, full document and original framing are preserved. Independent read-only source-layout inspection found exactly42 eligible rows,840 maximum allowed joint/weight bytes, no other accessor-view overlap, and no other primitive sharing these two accessors. Actual chest is skin slot3→node8; the code resolves names through `skin.joints`, not node-as-slot indexing. Source-layout evidence is source-layout.json; no candidate values were calculated.

`evaluate.py:16–27,98–143` binds the unchanged old50 evaluator to its own candidate module and calls its full gate on old50 only. The old implementation still requires its exact reconstructed bytes; new88 is separately compared to pinned old50 and permitted records. All90 local/global poses and old source-direction assertions remain, including unchanged binds and channels via whole-document/forbidden-byte preservation. Work changes are exactly the4 authorized identity fields.

`evaluate.py:65–95,145–169` uses exact pinned39 edge IDs and259 incident face IDs, independently regenerates incident membership from original topology, and records deformed endpoints/faces at the7 frozen keys. The two named edges and maximum over same39 must strictly shorten at89; any failed prediction emits STOP/nonzero after the bounded supplemental measurements. Both unchanged surface analyses retain original partition thresholds/budgets; their face memberships and changed IDs are recorded, with explicit noncomparability. No CLI/Web launch exists in either script.

`candidate.py:237–262` and `evaluate.py:181–200` have finite30s/240s alarms and convert errors/overrun into STOP/HOLD and exit1. Missing inputs fail at pinned-input checks. No exception becomes a pass. Existing surface budget remains its original bounded-check implementation, with the new240s outer alarm. One-shot process counter/output-freshness guards support, but do not replace, root's no-retry process rule.

## Independent synthetic verification

Executed only the reviewed synthetic two-record controls:

- `python3 -B experiments/88-m2-chest-local/test_controls.py`: exit0,11 cases,0 failures/errors; real constructor count0.
- `python3 -B -O experiments/88-m2-chest-local/test_controls.py`: exit0,11 cases,0 failures/errors; real constructor count0.

The tests call constructor-used `patch_binary`/`validate_binary`/`mix_record` seams with fabricated inputs. They cover forbidden bytes, positive loss and float32 underflow, nonfinite/negative/normalization errors, incorrect support/slots/capacity, exact first-zero operation, retained zero bits, JSON/length, fixed field endpoints and separate named-edge/maximum failures. Explicit require/raise plus unittest assertions survive -O. Output and commands are retained in independent-controls.json and associated stdout/stderr files. No real asset constructor input, current candidate run, real geometry measurement, old50 gate execution, build or UI was used as a test.

## Limits and release conditions

No code fix requested. Root may freeze these exact hashes and authorize the single real constructor/offline attempt. No retry or coefficient change is permitted after freeze; a failed/offline-incomplete attempt remains STOP/HOLD. Actual binary retention,90-key outcome, edge benefit and surface measurements are NOT-RUN until that attempt. Current normals/shading, between-key motion, CLI/runtime parity and visual gain remain NOT-RUN. Scalar smoothstep is not proof of mesh continuity or visible gain. Offline success alone cannot remove quality HOLD; actual same-key Web appearance must improve without a new259-face-band defect.

VERIFIED — exact code/source identities, source record layout, static acceptance wiring and11 synthetic cases in normal and-O. NOT-RUN — real constructor/offline, CLI/Web, normals/shading and visual benefit.
