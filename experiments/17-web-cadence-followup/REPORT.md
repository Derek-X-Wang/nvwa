# Bounded Web cadence follow-up — issue 27

**DEFER. Keep the current default profile.** The five planned pairs produced descriptive p95 changes within 10% for both workloads. They do not pass the strict adoption gate: document focus could not be read through the advertised DOM scope, and the browser presentation capability reported false at every endpoint. Document visibility was visible and AX focus identified the canvas. These observations are retained separately.

The root executor completed exactly 20 product navigations, in the predeclared order `A1 B1 B2 A2 A3 B3 B4 A4 A5 B5`; every arm ran idle Studio then finite Player. No failed or rejected run was replaced and no extra pair was added. The worker stopped UI execution after a blank-page capability check exposed a subagent visibility restriction. Root performed all product captures. The root-routed independent agent review is PASS for evidence integrity and the DEFER conclusion. It does not approve adoption. The worker's separate final raw reconciliation also passes.

## Observed results

These are Rust main-loop cadence percentiles. Positive change means B had a larger p95 interval. Every pair remains `valid=false` and `passes=false` because required focus/presentation conditions were not established. The numbers are descriptive evidence, not a strict gate pass or a causal result.

| Pair | Idle A p95 ms | Idle B p95 ms | Idle change | Finite A p95 ms | Finite B p95 ms | Finite change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 19.2000 | 20.7000 | +7.8125% | 18.9000 | 20.3000 | +7.4074% |
| 2 | 20.1000 | 20.6000 | +2.4876% | 19.3000 | 19.5000 | +1.0363% |
| 3 | 19.1000 | 19.6000 | +2.6178% | 19.6000 | 18.6000 | −5.1020% |
| 4 | 19.4000 | 20.2000 | +4.1237% | 19.5000 | 19.9000 | +2.0513% |
| 5 | 18.5000 | 19.1000 | +3.2432% | 19.4000 | 19.0000 | −2.0619% |

The frozen size gate is unchanged: A first-screen gzip is 20,539,196 bytes and B is 18,034,148 bytes, a **12.1964268% reduction**. Player adds the same 523-byte gzip Work to each arm. Exactly-once product inventories, gzip/no-store responses, manifest lengths and complete server body writes pass for all 20 navigations. Server writes do not prove browser receipt.

All 20 runtime reports contain 600 samples, BrowserWebGpu, physical 1280×720 at scale1, 18 joints, 9 skins, 9 meshes, 4 morph weights and the expected mode/Work/revision/playing/completed states. There are no captured runtime or console errors, and no collector errors. Each collection completed in 18.858–19.926 wall seconds, below the 45-second observation bound. Captured screenshots contain actual JPEG data at 1280×720; the API's saved raw names ended in `.png`. Publication candidates use `.jpg` names with byte-identical images and explicit hash mappings. Representative first-idle and final-finite screenshots were visually inspected.

## Conditions and limits

The frozen finite benchmark reports after its existing 15-second readiness warmup. Its recent 600-frame sample includes the completed held pose after the sequence reaches 9 seconds. It is a mixed active/hold sample. Motion-only cadence is NOT-RUN.

Document `visibilityState` was visible, `activeElementId` was `nvwa`, and AX focus identified the canvas at all observed endpoints. `document.hasFocus` is unavailable in the advertised read-only DOM scope, so focus is explicitly null with its reason. The browser visibility capability reported false at all 40 endpoints, despite the creation request asking for a visible tab. No focus or presentation success is inferred from the other observations. Continuous visibility/focus is NOT-RUN.

The machine had competing work. Available snapshots recorded `mediaanalysisd` at up to **264.6% CPU** and `node` at up to **156.7% CPU**. Forty process snapshots contained no recognized compiler executable names. This does not prove a quiet machine or continuously absent compiler work, and the observed CPU cannot be assigned causally to cadence changes. No unrelated process was stopped. Full process paths remain private; publication candidates contain aggregate CPU/process counts and compiler basename summaries only.

No new Cargo build, compiler/profile/features/assets/fonts change or product HTML/bootstrap/instrumentation change occurred for this follow-up. Root's build exclusion covered formal measurement. Navigation-to-ready, cold cache, GPU timing, display presentation timing, browser/GPU memory and browser body receipt remain NOT-RUN. These are local no-store observations with existing browser/Wasm/driver cache state and five pairs per workload.

## Identity and evidence

Before/after identity checks pass against the exact experiment16 decoded/encoded manifests, gzip pairings and static resource equality. Both complete Web bundle inventories are unchanged. The 45 historical compiled-source Git blobs match the frozen source base `11fc789e898119e0ed2b423f8a909dacb547f772`. This does not assert that another concurrently edited checkout equals the compiled inputs.

The five measured pre/post sealed files are `PROTOCOL.md`, `COLLECTION.md`, `followup.py`, `server.py` and `check-followup.py`. Their hashes match before and after; the exact original sources remain privately retained by root. Published copies under `reproduce/` are explicitly post-run copies with portable path/layout handling, optional helper-result output and redacted local paths. Their published bytes were not measured. `reproduce/source-manifest.json` records original and published hashes; `reproduce/MEASURED-TO-PUBLISHED.diff` records the changes, with the original local path redacted. No cadence or DEFER rule was weakened. Root's actual collector source is retained separately with final SHA256 `6c05c9b685a4c7ef108a0b1045e4fff42b8e55bfd9780b19cb453c9c6e262646`; it was **not included in the five pre/post seals**. No prior collector seal is claimed.

The first post-run audit assumed PNG from the filename and incorrectly reported screenshot format failures. Its public record is `evidence/public/audit-first-PNG-assumption.json`; the exact original audit and candidates remain privately retained. The corrected audit reads JPEG headers and passes all 20 images. This was an audit assumption error; no product measurement or image bytes were changed.

Authoritative raw evidence and exact measured originals remain privately retained by root. Public evidence is selected under `evidence/public/`: all 20 unchanged JPEG screenshots, complete consoles and collection records, HTTP inventories, 40 endpoint observations, chronological attempt ledger, aggregate process summaries, identity/source seals and cleanup. `evidence/public/screenshot-map.json` maps each original raw image name and SHA256 to its published `.jpg` copy. Complete private process paths are excluded.

`PUBLICATION_FILES.json` is the exact proposed commit inventory and hashes every selected file. It excludes original measured local-path files, discarded publication candidates and ignored authoritative raw data. Root owns final privacy review, preservation and publication. The published post-run verifier works against this selected layout:

```sh
python3 -B experiments/17-web-cadence-followup/reproduce/verify-publication.py
```

Reconciliation: `evidence/public/comparison.json`, `evidence/public/final-raw-audit-v2.json`, pre/post identity/seal files and `evidence/public/raw/attempt-ledger.json`. `reproduce/README.md` distinguishes evidence verification, post-run helper checks and a future lease-gated reproduction. Nothing here rebuilds the frozen bundles.

## Cleanup and verification

All ten owned server groups are absent. The A4 server had already stopped under its lifetime bound when cleanup observed it; its absent group is recorded. Root's final port check finds no listener on9201. Root browser inventory is empty, the viewport override is reset and visibility is restored to its initial false state. No task renderer or server remains.

VERIFIED — 20 root-executed captures, 10 descriptive pairs, frozen runtime/request/source/bundle checks, unchanged protocol seals and owned cleanup; strict adoption DEFER. Navigation/cold/GPU/display/memory/motion-only claims NOT-RUN.
