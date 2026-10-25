# Targeted R2 negative-result audit

Decision: **ACCEPT_NEGATIVE_RESULT**. No material finding blocks accepting this recorded STOP / NO-ADOPT result. This is not a visual, contact, admission or production pass. No correction cycle or retry is requested.

Scope: reviewed the new experiment87 code, README, frozen proposal/region, `main/RESULT.md`, `main/execution-receipt.json`, `main/construction.json` and `main/source-preflight.json`. No actual 96-vertex construction/evaluation was rerun. Fresh execution was limited to read-only hashes/receipt consistency and tiny synthetic rejection/mapping controls. No new candidate, source hunt, metrics, runtime, build or framework was created.

## Evidence

All four experiment-file byte counts and SHA256 hashes in execution-receipt match their current files. In particular `candidate.py` is 9750 bytes / `000cc9215cc1d265c71422fd5754809877cb670971730448ce6a6fcbee759ff6`; `test_controls.py` is 1881 bytes / `aa66a8b9a5d597f589979b506185ba77a57ee9f8700d48e9b7c0c09f41ded77d`. Experiment87's proposal and region match their task-main frozen copies byte for byte.

Current `git status --short` contains only untracked preexisting86 and new87, and tracked diff is empty. Experiment87 contains exactly candidate.py, test_controls.py, PROPOSAL.md, region.json and README.md. Its artifacts directory does not exist. This supports no derivative GLB/Work published by the inspected constructor; it is not a whole-disk absence claim.

The preflight receipt has exactly the frozen 96 IDs. Its reported maximum is the actual maximum of its recorded per-vertex residuals: `1.254442032749825e-7`, below unchanged `2e-6`. I verified receipt consistency, not a fresh full numerical reproduction. The recorded actual execution exited 1 with `original-fixture union discarded mass exceeds1%: 0.012913903560846783`. Construction.json and RESULT/README agree. The encountered value is **not** a maximum across an unfinished construction. The violating vertex and complete discarded-weight statistics are not retained in this STOP receipt; they remain UNKNOWN and are not needed to establish the threshold rejection. No additional investigation framework is warranted.

## Actual called path

- `candidate.py:71–87` authenticates control GLB, Work, region and author-source pins, loads the existing parser, resolves node22/primitive1, enforces the exact region and four-slot fixture. Original source segments at 42–49 match the previously reviewed author-to-glTF conversion, including positive glTF depth for the source's negative forearm/hand y.
- `source_preflight` at 90–104 resolves serialized slots through `skin.joints` before node names, reconstructs the applicable original torso/arm route, compares influences by name including missing support as zero, and retains the 2e-6 stop. The original .070 Gaussian and .0001 pruning constants/normalization are preserved at 62–68. The selected height range makes the simplified torso/arm branch valid for this frozen region.
- `construct` calls this preflight at 141 before creating its mutable binary copy or any blended weights. Lines 147–152 implement exactly the fixed x feather and y envelope in the accepted proposal. No key fitting or parameter sweep enters the formula.
- `four_slots` at 112–126 rejects nonfinite/negative values, sorts positive influences by descending weight and then actual node index, computes discarded mass before renormalization, and rejects mass above .01 at 117. Surviving node IDs map through `node_to_slot` before float32 serialization. The slot/node distinction is implemented correctly.
- The violating call at 153 raises before that vertex is written. Earlier selected rows may have changed the in-memory bytearray, but no asset write exists inside construct. Publication in main starts only after construct returns, at 181–191. The ValueError handler at 192–196 writes the STOP report and returns 1; `SystemExit(main())` at 203 propagates it. Therefore this particular rejection cannot leak a partial candidate GLB or Work through the inspected path.

The unexecuted success/publication branch and later byte-preservation, full diagnostic/runtime/CLI gates are not accepted as verified by this audit. They were not reached and need no expansion for a rejected pilot. Old50 predicates and all tracked source files remain unchanged.

## Controls and verification limits

The retained `test_controls.py` exercises meaningful seams:

1. It changes a saved source influence by .001, calls actual construct, and poisons four_slots with a RuntimeError. Catching the intended reconstruction ValueError proves the changed source is rejected before reaching the new-weight seam.
2. A five-way .2 distribution reaches actual four_slots and rejects .2 discarded mass before renormalization.
3. A NaN weight reaches actual four_slots and is rejected.
4. A chest/upper_arm.R .75/.25 case resolves returned slots through the actual loaded skin table and confirms the expected named influences.

These are three rejection controls plus a mapping check, not tests of visual improvement or full candidate preservation. Their execution PASS is retained in the author's receipt; I did not rerun the full test script because it invokes the real region's source preflight and a modified full construction call.

Fresh reviewer-only tiny checks passed: five-way .2 mass rejection; NaN rejection; explicit chest node8→slot3 and upper_arm.R node7→slot9 serialization; and an injected immediate preflight failure through actual construct with proof that four_slots is never reached. These checks use synthetic inputs and do not recompute the pilot. Fresh hash, frozen-copy, sample-ID/maximum consistency and artifact-absence checks also passed.

## Claims and final disposition

RESULT/README correctly distinguish the earlier retained-image/geometry diagnosis, source-rule reproduction, and rejected construction from missing new mechanism/surface, CLI, build and current Web evidence. The one blend did not pass its construction condition, so stopping before those later gates is correct. This result does not refute or prove source-route discontinuity as the visible notch's cause; the counterfactual was never admitted for appearance testing. No second parameter choice or comparison is authorized.

The inspected reports do not claim a better shoulder, better contact, completed M2, or adoption. B1 full-positive influence policy, all old gates/failures, #80 HOLD, 99-point backup/full21-before-fit, #112 original FAIL, #3 blocked and #4 gaps remain intact. The earlier hair review remains a bounded local UNKNOWN/no-download/no-admission assessment; no new source search was performed here.

**VERIFIED —** hashes, frozen copies, receipt consistency, current scope/no artifact directory, actual called rejection path, and tiny synthetic controls. **RETAINED EXECUTION —** 96-vertex source preflight and actual constructor exit1 as recorded by the main worker; not rerun by reviewer. **NOT-RUN —** new candidate completion, mechanism/surface/CLI/build/current Web/native/CI and visual/admission acceptance.

Only this RESULT-REVIEW.md was written during the targeted audit. All child shell calls completed; no persistent process, server, tab, port or agent was created. Writes stop on return.
