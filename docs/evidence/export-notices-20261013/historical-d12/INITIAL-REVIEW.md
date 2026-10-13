# Independent R2 review — initial candidate

Verdict: **NO-GO for publication of the experiment tooling as currently claimed.** Three P2 findings below require bounded fixes and targeted re-review. The retained actual download evidence is usable, and the notice candidate reproduces byte-for-byte. This is not a legal or distribution approval.

Reviewed checkout: `/Users/derekxwang/.codex/worktrees/m11-ui-integration/nvwa`, branch `codex/m11-export-notices`, HEAD/base `7851c2e74f757f93774f2d5fa05151562c393012`. Reviewed only experiments 35 and 36; current root checkpoint/publication documents were not yet supplied. No reviewed files were edited. All 1182 reviewed file hashes remained unchanged. Tracked diff against base was empty; only both experiment directories and preexisting `.tools`/`target` were untracked.

## Findings

### P2 — Source provenance and source-cohort checks accept changed or absent evidence

Affected: `experiments/36-distribution-notices/check.py:20-34,57`.

The checker hashes listed copied files, but does not reconcile their provenance against the preserved source records. Its entire source comparison check accepts any list whose supplied `equal` flags and paired hashes agree, including an empty list. In separate copies of the real 323-package candidate, each of these changes still returned exit 0 / VERIFIED-INTEGRITY/PARTIAL-COVERAGE:

- Set `source_comparisons=[]`.
- Replace one entry's `current_sha256` and `retained_sha256` with 64 zeros.
- Change the indexed craft-ui NOTICE's `source.relative_path` to `WRONG-NOTICE`.

These are independent single-field/data-entry regression controls, not coordinated changes to every trusted anchor. They contradict the reported source/notice provenance integrity guarantee. Reconcile the exact required source path set and hashes against the already retained build-input manifest, and validate notice source path/hash relationships against package manifests and supplement records. Retain explicit limitations where a field cannot be checked offline. Add red/restored-green controls on actual pack copies.

### P2 — Required asset inventory and preserved unknowns can disappear while the checker stays green

Affected: `experiments/36-distribution-notices/check.py:49-58`.

The asset/font checks only iterate the supplied lists. Gap checks require missing-text and null-license package sets, then only require some gap to remain. Separate mutations all returned exit 0 / VERIFIED-INTEGRITY:

- Delete the entire `embedded_default_font_candidates` inventory.
- Delete the entire distinct `assets` inventory.
- Keep only missing-license-text/first-party-owner-license-decision gaps, silently removing legacy-expression, SDK, system-library, generated-JS, CC0, and signing boundaries.
- Change `root_first_party_license` to `MIT; owner approved`.

The top-level BLOCKED flag still prevents full release approval, but the checker has accepted loss of precisely the scoped obligations and owner-policy uncertainty this candidate exists to preserve. Bind required asset IDs, font payload/hash/notice references, gap families, and owner-policy fields to retained facts or an explicit frozen schema. Do not invent a first-party license or turn unresolved scope into compliance. Both this finding and the first have raw mutated outputs plus restored greens in `independent-mutations.json`.

### P2 — Supported DOM journal hides overflow

Affected: `experiments/35-web-export-followup/observer.js:13-15`.

On reaching 64 records, `record()` increments `dropped` and returns before updating the DOM journal. An independent DOM-backed control with 100 console errors forwarded all 100 originals and retained 64 records, but exposed `window.dropped=37` versus journal `dropped=0`. The supported browser read path is this journal; the raw run explicitly could not read the custom Window property. Thus a saturated journal reports zero loss even if later errors/callbacks were dropped. Existing Node tests omit document/journal and miss this case. Keep overflow accounting observable through the supported bounded DOM surface and add a DOM-backed control.

Actual case 2 contains only two records, so this does **not** invalidate its retained callback, PNG, or inconclusive result. Preserve the original case observer bytes/network receipts. A hardened future helper must be distinguished from the immutable historical run, not substituted into it.

## Independent verification

- Experiment 35: 2 Node + 7 Python controls pass; offline receipt verifier passes. Opened both actual downloaded PNG copies independently: real character/editor UI, revision 0 and idle timeline, distinct animation instants, 1280×720 RGB. Sizes/hashes match original path receipts: 326061 bytes / `1c7cb42f…` explicit; 306354 bytes / `e62a9bb7…` automatic.
- Matched original adapter screenshot data-URL bytes to the two preserved JPEGs and matched extracted Rust callback objects to actual adapter log text. Read all event wait calls/outputs, console context, server network records, file-time receipts and exact cleanup records. Before-navigation listener timeout remains only a bounded event non-observation; no missing-file or causal conclusion follows. Case 2 changes listener lifetime, observer storage and five-second pre-init timing; these confounds remain explicit. Tool click is not physical human input.
- Rehashed all 32 actual source-cohort files and 5 current artifact inputs against experiment 35 receipts. Actual Wasm, common work and GLB remain the accepted cohort. Server source has only an exact file map, strict Host/Origin checks, no receiver or listing, and bounded HTML changes. No browser/render/download/server run was started by reviewer.
- Experiment 36: independent locked/offline collection reproduced manifest `ab92b4816b18191e0d24d063e43a9e183cd3204114a4321da5d478455a403bf2`, 323 union resolver inputs, 1039 files and 45 gaps. Normal+build target counts 307/278 and native CLI feature-unification comparison are retained; these are not final linked membership.
- Ran all 18 supplied checker controls with expected red/restored-green/completeness outcomes. Independently checked 323 local package manifests/VCS records, 583 local notice copies, 87 shared-root copies, 24 pinned public source copies, six original asset notice copies and six retained build records against actual source bytes. Checked all ten primary response hashes and precise repository/commit supplement joins. Epaint subfont notices, Nvwa Sans derivative, original CC0, craft-ui root notices and first-party null metadata remain distinct.
- The current pack is factually consistent under these independent checks. Findings concern false green regression protection, not an identified wrong current license expression or source byte.

## Limits and handback

No new UI, GPU, native export, build, signing, notarization, clean-machine, public binary, network primary re-fetch or legal approval. Original issue 5 cause remains unknown; issue 10 completeness remains blocked, 21 missing text candidates (three first-party) and owner policy unresolved. Issues 3/4 remain blocked/unverified as dispatched. No product, dependency, old experiment, 190-case performance archive, Git state, root policy or package changed.

Receipts are private under `.work/export-notices-r2/`: baseline-0..4.json, controls-evidence/, independent-mutations.json, observer-dom-overflow.json, collector-reproduction.json, independent-provenance.json, before/after-hashes.json and postrun-reconciliation.json. The first private provenance parser selected escaped DOM text before actual logs and failed; its error is retained separately and its correction passes. Only synchronous finite CPU subprocesses ran; the collector subprocess was reaped. No owned persistent processes remain. **QUIESCENT**; no full agent-instance teardown claim.
