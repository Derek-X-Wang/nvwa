# Independent acceptance: frozen initial scopes

Decision: **GO for M1.1 administrative closure** and **GO for the bounded issue #13 evidence conclusion / issue #12 NO-GO feasibility report**. No blocking defect found in reviewed candidate bytes. This is not acceptance of M1.2 CLI, GUI continuation, final publication, current-main runtime, general retargeting or real model inference.

Reviewed HEAD was `a6cb13eeadeae0e30b42c9307286d9c84c49286b`; ROADMAP/history/experiments39/40 were new or modified working-tree bytes. `reviewed-inputs.json` binds them by SHA-256. Read AGENTS.md, GLOSSARY.md and ADRs 0003–0005. Implementer confidence and chats were not used as proof. Candidate reports were treated as claims and checked against raw artifacts/source.

## Findings

No P0/P1/P2 finding. No changed invariant detected within the reviewed scope. Remaining limits below are explicit boundaries, not hidden passes.

## M1.1 administrative reconciliation

- Independently fetched PR file pages and PR metadata, using full pagination: #22 `[100,11]` =111; #28 `[100,69]` =169; #29 `[100,49]` =149. Each exactly matches API `changed_files` and inventory order/path list. Exact heads and base branch names match. All 429 declared paths were checked against Git objects at their archived head and `a094baa048e6e50056e3288ecfa85bb4ac62e140`: zero mismatches. #22 has 105 absent /6 later-different; #28 168 absent /1 later-different; #29 149 absent. These bytes are not falsely represented as merged.
- Original roadmap snapshot is byte-for-byte equal to `a094baa:docs/ROADMAP.md`, SHA-256 `82f6cd61a262f70709d8f0a929fc9127fd0b1b67732563f056668e41c15bc04c`.
- All three PRs were OPEN and unmerged during this audit. Exact local and origin branch refs still point to their archived heads. Public commit-tree URLs bind those heads. Closure disposition explicitly preserves branches/PR objects and rejects old product-source adoption.
- Fresh issue API reads show #3 OPEN /needs-info with the original unavailable DPR trigger and all acceptance criteria retained; #4 OPEN with original first-presentation/cold-state/stall/GPU-memory/timing criteria retained. ROADMAP explains these gaps, does not call cadence/readiness presented performance, and keeps M2 out of current implementation scope.
- GO permits closing the old experiment PRs without merge/branch deletion and closing the M1.1 milestone as administrative delivery closure while keeping #3/#4 open. It does not authorize deleting unique historical evidence or claiming those original acceptance criteria passed. External closure was not performed by this reviewer.

Evidence: `archive-results.json`, `pr-*-files-pages.json`, `pr-*-metadata.json`, `issue-{3,4}.json`.

## Issue #13 controlled derivative playback

- Independently verified all 61 manifest file hashes. Source and private copied GLBs match the published original/experiment04 hashes; six public/private Works match byte-for-byte, their embedded asset hashes and clip index 2 match actual GLB animation order, appearance parameters are zero and scale is1.
- Original baseline and private renderer executables independently hash to `3be9380f1747c8a6266c59e49f73550e180038fb1259187942af16033a2bc929`. Report correctly calls this an older frozen renderer cohort, not current-main acceptance. Current source camera constants match the claimed fixed camera. No claim of a rebuilt/instrumented binary was used.
- Inspected retained full reference/naive/corrected 1.25s images and full contact sheet. All 1.25s images visibly show paused Play, Ready, Active:wave and 1.25s. Naive chest/arm deformation is visibly different; corrected matches the reference overhead wave. Independently recalculated pixel metrics for all18 fixed-time images and both rest comparisons; every value equals retained metrics. Rest differs by one pixel/one level. Six parsed renderer receipts support actual skin readiness and active-versus-empty animation state. Incidental cadence fields are not performance evidence.
- Inspected retained corrected live-a/live-b images: Pause is visible (running), times are2.7094 and1.0322 and actual character poses differ. Independent scene pixel differences for both naive and corrected live pairs are nonzero. These corroborate actual changing animation rather than only static pose renders. This reviewer did not conduct a new live UI run.
- Independently repeated unchanged experiment04 CPU numerical script into reviewer-owned scratch. It exits0; resulting full metrics JSON exactly equals retained rerun metrics, including all19 times,18 joints,24,736 vertices, rest and identity controls, four degenerate-input errors and exact derivative hashes. Corrected max joint error2.16774327513e-8m and vertex error3.08111128912e-8m; naive max joint/hand0.800824139986m and vertex0.868395833353m. Six visual times join exactly to numerical sample times.
- Supported conclusion stays limited to the fixture's explicit signed-axis rest-basis conversions with equal anatomy/topology/lengths. No semantic remap, different proportions, IK/contact, root-motion policy or arbitrary-rig claim is made.

Evidence: `artifact-results.json`, `numeric/{metrics.json,target-*.glb}`, `numeric.stdout`, retained experiment40 sources/logs/screens.

## Issue #12 readiness and source reconciliation

- Fresh current-Python/PATH/named-cache read-only probe at2026-10-14T23:22:39Z agrees with the bounded environment claims: Apple M2Pro/16GiB, Python3.14.7, no named Kimodo/PyTorch/transformers/LLM2Vec packages or selected executables, named cache roots absent, no configured model roots. This is not an all-disk search or claim about every interpreter.
- Independently reran static source analyzer; all38 captured public response hashes pass. Pinned checkpoint config identifies SOMASkeleton30/30fps; AST arrays count30/77 and official model methods contain both expansion call sites. Direct source inspection confirms relaxed-hand rest initialization, copied source subset, recomputed forward kinematics and4→6 contacts. Existing actual GLB parses as one18-joint skin with unchanged asset hash and authored idle/turn/wave. No actual checkpoint arrays were generated or inspected.
- Independently refetched three bounded public text endpoints: pinned NVIDIA config, pinned NVIDIA model metadata and pinned official skeleton source. All return200 and exact SHA-256 equality with implementer captures. The web tool could not open the HuggingFace config, so a bounded stdlib HTTP read confirmed it instead. Primary source: https://raw.githubusercontent.com/nv-tlabs/kimodo/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/skeleton/definitions.py .
- Read exact source/metadata for separate code/checkpoint/base-encoder/adapter terms, offline fallback, official environment guidance and alternate-backend manifests. Current captures distinguish Apache code, NVIDIA model terms, gated Llama base terms and adapter MIT metadata; no license acceptance or use approval is inferred. LOCAL_CACHE misses can still download upstream, and the report explicitly excludes that path from a future offline run.
- Recomputed reported payload estimates and43 manifest size/42 LFS-hash joins; values match. Missing final-norm metadata hash is retained. Artifact byte totals and official ~17GB GPU guidance are not presented as measured resident RAM or Mac performance. Alternate C++ path remains uninstalled/unrun, and proposed mapping remains unvalidated.
- NO-GO is supported for this bounded current environment/authorization scope. Actual output reconciliation, resource measurements, inference, generated-action playback and cancellation remain NOT-RUN, with authored actions never renamed as generated.

Evidence: `fresh-local-environment.json`, `fresh-schema-metadata.json`, `fresh-public-text-receipts.json`, `fresh-*` raw text captures; read-only original `.work/m12-motion-readiness/sources`.

## Review limits and cleanup

NOT-RUN: M1.2 experiment38/CLI repaired source, fresh runbook operator acceptance, new GUI continuation evidence, final PR CI, merged-main verification, live GUI/Web/GPU runs, Bevy build, real model execution, weight downloads or legal/distribution approval. Waiting for orchestrator's later fixed-CLI/runbook freeze.

Reviewer mutations are restricted to `.work/m12-independent-acceptance/**`. No source/Git mutation, commit, external write, install, live UI action, weight request, new server, persistent worker or subagent was created. Numerical subprocess completed/reaped; GitHub/HTTP reads completed. Reviewer scratch is intentionally retained for parent audit.

VERIFIED — Full429-path archive reconciliation; original roadmap bytes; fresh open #3/#4 state;61 evidence hashes;18 image metric recalculations; three rest renders; exact19-sample numerical rerun; fresh local readiness probe;38 source hashes and three exact fresh public-text confirmations.
