# 44 — One approved genuine raw CPU motion sample

**One authorized local CPU attempt produced genuine raw model output. Both raw files have the expected sizes and hashes, and numeric structure checks pass.** This does not admit signed axes, normalized motion, target mapping, prompt meaning, motion quality or Nvwa playback. M2 and [#12](https://github.com/Derek-X-Wang/nvwa/issues/12) remain OPEN.

Recorded 2026-10-15 on the same busy Apple M2 Pro / 16 GiB Mac used for [experiment 41](../41-real-short-motion/REPORT.md). That report remains the unchanged pre-run snapshot. This follow-up used its exact frozen source, private CPU executable and guard. It changes no product source, Work, asset, Cargo dependency or renderer. Three offline commands are appended to the existing portable CI motion step: this evidence verifier and experiment 45's numerical study and controls. CI does not acquire models or run inference. No job, timeout, resource or dependency setting is added. A passing experiment 45 check means its numerical HOLD study and controls pass, not that playable motion is admitted. No authored action was relabelled generated. The two published F32 files are raw output from the pinned community C++ port; no official decoder parity is claimed.

## Authorization and exact acquisition

The human approved the exact three-file proposal and one bounded offline CPU attempt. The [public authorization summary](evidence/authorization-public.json) records that scope without copying the private human reply. [The one-attempt ledger](evidence/one-attempt-ledger.json) was created and fsynced before controller launch. The one-attempt permission is **consumed**. It does not authorize another download, retry or ledger reset.

The unchanged acquisition script streamed exactly **6,198,789,742 bytes** once. Each partial had to pass the expected byte count and SHA-256 before rename. It exited 0 in **221.385803 s** with exact stdout `Verified 6198789742 exact model bytes; inference not started\n` and empty stderr. There was no fallback or retry. The script did not separately expose HTTP response status; that value remains UNKNOWN. Pinned root URLs are retained in the [acquisition receipt](evidence/acquisition/receipt.json); no signed redirect query URL is published.

| Private model artifact; weights are not published | Revision | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `kimodo-soma-rp-v1.1-f32.gguf` | `65f8b8ab34ee7524161cc87b20ae4cb4f5d3a12d` | 1,133,166,784 | `3bf1229f4c1eff1d28f5196a854113da2df9a11a5e21c60694630903bf948ee4` |
| `Llama-3-Kimodo-Q4_K_M.gguf` | `3e8d958803beaddb6011ac534f2be972e2710c7d` | 5,058,327,904 | `c06f2cb6a7615e949bcbb5b582ad35a191338b68b5a51abe17d259ebe574c005` |
| `tokenizer.gguf` | `3e8d958803beaddb6011ac534f2be972e2710c7d` | 7,295,054 | `81614aca62a98846c02b72cc2e5378e5bdce8b4d507b88f96eb1faa90dae607e` |

Code is pinned to kimodo.cpp `5679ff19ba0a522c0b0516e9a9d402fe1af2c027` and GGML `8c63e70982c95ceb862e3a1073a2c1beef75d60a`. The unchanged guard checked the local model, executable and dylib identities. Its compiler/runtime-bound native-float prerequisite replayed successfully: little-endian IEC559 binary32 `1.0` emitted `0000803f`. The executable hash is `55b5c74fb7ab8c83d1560476eb2b9a29e184cbc7020181f3d6eeef44840e9f7d`; full identities are in the [generation receipt](evidence/run/generation-receipt.json) and earlier [float prerequisite](../41-real-short-motion/evidence/float-prerequisite.json).

No terms acceptance, login, credential lookup, extra packages/source/builds/models, paid API, cloud compute or extra machine was used in this approved trial. No weights, executable, dylib, tool archive, source cache or certificate is published. Separate code/model/encoder terms remain linked in [experiment 41](../41-real-short-motion/REPORT.md#exact-proposed-model-acquisition--not-executed); this result supplies no new upstream endorsement or redistribution rights.

## Exact one-attempt result

Prompt: `A person stands in place and waves their right hand.` Seed **42**, **90 frames**, **30 fps**, **25 diffusion steps**, text/constraint CFG **2/2**. The run was CPU-only with four threads, text layer chunk one and a 1024 MiB text residency setting. Its child environment contained explicit CPU/offline settings and no inherited account tokens or proxies; macOS sandbox denied network access.

The guard launched provider PID/PGID **41445** at `2026-10-15T17:48:17.191545+00:00`. It finished with **reason `exited`, exit 0**, exact stdout `generated 90 frames with 30 joints\n` and both complete raw files. The retained [stderr](evidence/run/process/stderr.txt) contains 12,137 bytes of profile lines, including exactly 25 descending diffusion steps, indices 24 through 0. The controller and directory inventory support **one physical producer attempt**, not a tamperproof global host audit.

| Observation | Result and boundary |
| --- | --- |
| Guard elapsed | **58.545243 s**, including monitoring and bounded cleanup |
| Controller elapsed | **62.212862 s**, including prerequisite/model hash checks and guard invocation |
| Maximum sampled group RSS | **1,234,583,552 bytes** (1.149795 GiB), from 544 samples; not an instantaneous hard peak, all mapped model bytes, virtual memory or host-total memory |
| Stop settings | 600-second monitoring stop; 7 GiB sampled group RSS stop, nominal 100 ms polling; 8 GiB was only a planning ceiling, not an OS hard cap |

This is one observation on a busy 16 GiB machine. Readiness hash checks had just read all model files, so page cache was warm or warm-cache eligible. No cold-cache reset or repeat was performed. These numbers are not a cold-start benchmark, a general performance result or a promise that another request fits.

| Published raw output | Shape | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| [root positions](evidence/run/raw/root_positions.f32) | `[90,3]` | 1,080 | `dcc221d506999a803b1d0fddef87abc0131b1e8f4e64187bc57fde3a63c204af` |
| [parent-local XYZW rotations](evidence/run/raw/local_rotations_xyzw.f32) | `[90,30,4]` | 43,200 | `67914c5d72c54429bf8a70d3f9ef43157fb5181fa36ab2c5f8ce7f9dc69d3a55` |

Offline little-endian binary32 parsing found **11,070 finite scalar values**: 270 root components plus 10,800 quaternion components. All **2,700 quaternions** are nondegenerate. Norms span `0.9999999158736569`–`1.0000000817999215`; maximum absolute norm error is **`8.412634311394385e-8`**. [Derived numeric structure](evidence/numeric-structure.json) and the [independent post-run review](evidence/reviews/post-run-review.json) agree.

The raw stream has no stored timestamps. Under the stated `i/30` sampling convention, 90 samples run from **0 to 89/30 = 2.9666666667 s**; the nominal frame budget is **3 s**. No extra endpoint or quaternion normalization was added. The output matches this C++ port's 30-joint layout; official SOMA77 expansion and official decoder parity remain untested.

## Independent review, resources and cleanup

[Pre-run review](evidence/reviews/pre-run-review.json) accepted the frozen code/runtime and held launch for completed models. [Readiness review](evidence/reviews/readiness-review.json) independently hashed all three local files before root sent RUN GO. [Post-run review](evidence/reviews/post-run-review.json) accepted genuine raw provenance and numeric structure, while keeping axes, normalization, mapping, semantics and playback unadmitted. The source post-run review SHA-256 is `1ecbb6ef958c994393e0902ceefaf83e4db513b34032bc34b6d8f78e84e0bc32`; the publication retains its exact bytes.

| Resource snapshot | System memory free | Swap used |
| --- | ---: | ---: |
| Before acquisition | 36% | 12,701.75 MiB |
| Before inference | 39% | 12,753.12 MiB |
| During observed inference | 44% | 13,757.44 MiB |
| After completion | 51% | 13,677.44 MiB |

These are system-wide snapshots from `memory_pressure -Q` and `sysctl vm.swapusage`, not workload-attributed physical memory measurements. Before inference the disk reported 271,393,924 KiB available; afterward 270,339,180 KiB. No critical pressure was observed in the retained snapshots. Unrelated apps/processes were not closed or killed. [Original resource records](evidence/resources/resources-before-inference.json) and [post-run cleanup](evidence/resources/resources-after-and-independent-cleanup.json) preserve their timestamps and exact commands.

The guard sent TERM to its owned group during teardown, recorded no cleanup errors and verified absence. Independent fresh `ps` queries found provider PGID 41445, guard PGID 41353 and wrapper PID 41343 absent: exit 1 with exactly empty stdout/stderr. Acquisition PGID 31851 and wrapper PID 31841 were also independently absent. The [post-run reviewer](evidence/reviews/post-run-review.json) repeated exact-owned-process checks. Private weights/runtime remain retained by the parent; no live task-owned process remains.

## What this closes and leaves open

This result can close [#54](https://github.com/Derek-X-Wang/nvwa/issues/54)'s bounded experiment **after reviewed publication is merged**. It does not close M2 or [#12](https://github.com/Derek-X-Wang/nvwa/issues/12). The remaining gates are signed-axis/handedness checks, normalized schema and source rest convention, root trajectory applied exactly once, target skeleton mapping, semantic/quality assessment, and actual generated native/Web playback. The exporter’s 0.988 m rest-height default must not be silently added to these raw root samples. [Experiment 45](../45-genuine-rig-admission/REPORT.md) studies this same sample and holds playable admission for actual root/neutral-pose/semantic mapping gaps; it does not alter this raw-generation success. [Experiments 42/43](../../docs/evidence/m2-authored-controls/ACCEPTANCE.md) remain authored import/mapping controls, not admission of this generated sample. #3, #4 and #49 are unchanged.

## Offline verification and historical commands

From the repository root, reproduce the retained hash, JSON, receipt, numeric and cleanup-record checks without models, credentials, packages, compilation or inference:

```sh
python3 -B experiments/44-approved-cpu-motion-trial/verify_evidence.py
git diff --check
```

[SHA256SUMS.json](SHA256SUMS.json) inventories every other file in this experiment, including the verifier, report, exact receipts and both raw arrays. The index excludes itself to avoid a circular hash. [Copy provenance](evidence/copy-provenance.json) records original source hashes and explicitly records **no transformation**. Absolute paths in archived receipts are historical task-local provenance; this checkout does not contain those private models or executables.

The verifier rejects optimized Python (`-O`, `-OO`, or `PYTHONOPTIMIZE=1/2`) before reading the evidence, including when its `main()` is called after import. This explicit non-assert runtime check preserves its assertion-based verification checks. The [publication-review history](evidence/publication-review/README.md) retains the exact initial P2 HOLD review, original verifier as inert text, and red/green control receipts: the old optimized verifier falsely passed a ledger changed to count2 with stale hashes, while the corrected CLI and imported `main()` reject optimized modes. The actual retained model evidence was valid and was not changed by this correction. Historical verifier text is never executed by CI.

A second P2 review found that the request comparison only checked keys present in the receipt: a missing seed or empty request could pass after private hash rebinding. The current check requires equality with the complete ten-field request defined by the unchanged run guard: code/GGML revisions, artifacts, prompt, seed, frames, fps, steps and both CFG values. Missing or extra keys and wrong values reject. The [exact reviewer red receipt](evidence/publication-review/request-shape-red.json) and inert pre-correction verifier preserve the failure history; private rebound-fixture controls cover missing seed, empty request, extra key and wrong seed through CLI and imported `main()`. The actual generation receipt already contained all correct fields and remains unchanged.

The following are the **already executed historical commands**, retained for audit, not instructions to run again. Their approval has been consumed; any new model attempt needs separately scoped approval. Do not reset the ledger or replay these commands under the old receipt.

```text
/opt/homebrew/opt/python@3.14/bin/python3.14 -B experiments/41-real-short-motion/acquire_models.py --approved-download .work/m2-provider/authorization-2026-10-15.json
/opt/homebrew/opt/python@3.14/bin/python3.14 -B experiments/41-real-short-motion/run_guard.py --approved-run .work/m2-provider/authorization-2026-10-15.json
```

VERIFIED — Exact three-artifact acquisition; one genuine offline CPU attempt; completion/stdout/raw sizes and hashes; finite/nondegenerate numeric structure; independent review and owned cleanup; frozen 41–43 and historical acceptance bytes unchanged.

NOT-RUN — Signed axes/handedness, normalized schema/rest/root admission, target mapping, semantic success/quality, generated Nvwa playback, physical-human assessment, official decoder parity and cold-start/performance benchmarking. Publication review, current-candidate CI and merged-main CI are separate gates and are not supplied by this local evidence check.
