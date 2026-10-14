# 39 — Genuine motion provider readiness

**Decision: NO-GO for a genuine local model run in this stage.** Current local runtime and authorized weights are unavailable in the checked locations. No model was executed. A smaller C++ backend is a candidate for a separately authorized feasibility run, not an available provider. Stop this investigation here; do not implement M2 or change the product to hide the blocker.

Observed on **2026-10-14**, approximately **23:14 UTC / 16:14 PDT**, against issue [#12](https://github.com/Derek-X-Wang/nvwa/issues/12), updated 2026-10-11. Read the original brief sections 6.2/M2, current implementation contracts, glossary, and experiment 05. This stage adds only this directory and private `.work/m12-motion-readiness/` receipts. It creates no generated action, adapter, runtime change, or fixture change.

## Finite readiness matrix

| Requirement | State | Evidence and next decisive input |
| --- | --- | --- |
| Exact public code/model/encoder identities | AVAILABLE as candidate pins | Tables below and metadata receipts. These are identified artifacts, not authorization to acquire/use them. |
| Separate code, checkpoint, encoder, asset terms | AVAILABLE for review; authorization UNKNOWN | Owning instruments identified below. No acceptance, credential inspection, access request, or legal approval. Next input: explicit approval for the chosen exact local artifacts and terms. |
| Compatible installed official runtime | BLOCKED | Current Python has no Kimodo/PyTorch/transformers/LLM2Vec. Next input: an authorized isolated runtime with tested Python/dependency versions. |
| Exact authorized local weights | BLOCKED | Named cache/runtime paths absent; no configured model/cache roots. This is not an all-disk search. Next input: named local artifact paths and authorization, with hashes matched to the chosen revisions. |
| 16 GiB official full resident path | BLOCKED for planning | Official docs say about 17 GB GPU memory. BF16 base plus F32 motion parameter payload alone is about 16.013 GiB, before adapters/activations/OS. CPU encoder placement does not create separate memory on this unified-memory Mac. No measured peak is claimed. |
| Smaller local backend | UNKNOWN | C++ CPU/quantized path has smaller artifact payloads, but no installed executable/toolchain or measured Mac run. Next input: separately approved isolated setup and a bounded CPU run. |
| 30 versus 77 schema drift | AVAILABLE as static explanation; actual output UNKNOWN | Pinned config, AST joint counts, conversion call sites and export docs agree: predict 30, official public API/export 77. Next input: inspect arrays from a genuine run of these exact artifacts. |
| Mapping into the existing 18-joint target | UNKNOWN | Existing skin has 18 joints; mapping proposal below is not a retargeter. Next input: genuine source motion plus calibrated rest poses and runtime playback. |
| Model latency, memory, quality, cancellation, playback | UNKNOWN / NOT-RUN | No inference, tensor work, generated output or playback. Next input: an authorized run with process memory/time receipts and acceptance observations. |

## Pinned candidate identities

Pinned responses and dates are recorded in [source-receipts.json](evidence/source-receipts.json). Dates below are upstream commit/update dates, not the local observation date.

| Component | Exact revision | Upstream date |
| --- | --- | --- |
| [Official Kimodo code](https://github.com/nv-tlabs/kimodo/tree/58e781898b3d7e328a676a75d3e338c45dce3ad9) | `58e781898b3d7e328a676a75d3e338c45dce3ad9` | 2026-09-22 |
| [SOMA-RP-v1.1 checkpoint/config/card](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1/tree/6c9233af1180b8151e3c4703477104af5dce9dd5) | `6c9233af1180b8151e3c4703477104af5dce9dd5` | 2026-04-10 |
| [Meta-Llama-3-8B-Instruct base encoder](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/tree/8afb486c1db24fe5011ec46dfbe5b5dccdb575c2) | `8afb486c1db24fe5011ec46dfbe5b5dccdb575c2` | 2025-06-18 |
| [LLM2Vec MNTP adapter](https://huggingface.co/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp/tree/31474e395ada192e8ed1586db6be79fb3b70c9c0) | `31474e395ada192e8ed1586db6be79fb3b70c9c0` | 2025-12-02 |
| [LLM2Vec supervised adapter](https://huggingface.co/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised/tree/baa8ebf04a1c2500e61288e7dad65e8ae42601a7) | `baa8ebf04a1c2500e61288e7dad65e8ae42601a7` | 2024-04-30 |

The pinned [loader](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/model/load_model.py) selects the two McGill adapters, BF16 and 4096-dimensional embeddings. Adapter configs name the Meta base and have `revision: null`; the loader's normal hub resolution also omits a revision. Thus these are proposed reproducibility pins. Running upstream defaults would not itself prove the pins were honored. Notably, `LOCAL_CACHE=true` still falls back to a download on a cache miss. A future worker must enforce offline behavior and explicit local paths outside this fallback.

Public metadata reports **283,281,777 F32 motion parameters**, **1,133,185,036 checkpoint bytes**, and a base encoder with **8,030,261,248 BF16 parameters**. The model card rounds the motion model to 282 M; preserve that distinction rather than silently treating the card as exact. Each adapter payload is 167,829,552 bytes. No tensor payload was fetched. [Pinned model metadata](https://huggingface.co/api/models/nvidia/Kimodo-SOMA-RP-v1.1/revision/6c9233af1180b8151e3c4703477104af5dce9dd5?blobs=true), [pinned base metadata](https://huggingface.co/api/models/meta-llama/Meta-Llama-3-8B-Instruct/revision/8afb486c1db24fe5011ec46dfbe5b5dccdb575c2?blobs=true).

The official [environment guidance](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/README.md) describes Linux development, NVIDIA GPU testing and a CPU encoder option. Its [installation instructions](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/docs/source/getting_started/installation_virtual_env.md) report Python 3.10+/PyTorch 2.0+ testing; package metadata's `>=3.8` declaration is not proof of Python 3.14 compatibility. No Apple Silicon performance or support claim follows from these documents.

## Schema reconciliation and target implications

The pinned [checkpoint config](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1/blob/6c9233af1180b8151e3c4703477104af5dce9dd5/config.yaml) uses `SOMASkeleton30`, 30 fps and a 4096-dimensional text input. The [model card](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1/blob/6c9233af1180b8151e3c4703477104af5dce9dd5/README.md) describes 30-joint rotations and at most 300 frames/10 seconds. The [official skeleton source](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/skeleton/definitions.py) defines both 30- and 77-joint schemas. Expansion inserts relaxed-hand rest rotations, copies predicted joints and recomputes global poses. It does not generate new independent finger motion. The [external model methods](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/kimodo/model/kimodo_model.py) call this expansion in both single/multi-prompt output paths. Source parsing confirms both call sites; it does not execute them.

The [export specification](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/docs/source/user_guide/output_formats.md) distinguishes 77-joint SOMA NPZ from older 30-joint files. NPZ uses root positions and local/global rotation matrices. BVH uses 77 joints and meters-to-centimeters scaling; its default rest pose differs from standard-T-pose NPZ. One remaining documentation mismatch: the generic NPZ list says four foot-contact channels, while the SOMA expansion source explicitly emits six. A future adapter must check the actual skeleton, dimensions and channel layout; it must not infer them from the model name or file extension.

The existing Nvwa GLB SHA-256 remains `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`. The stdlib probe reads **one skin, 18 joints**, with authored `idle`, `wave`, `turn` animations. It does not modify or play them. Proposed mapping intent:

| Nvwa target | SOMA source intent | Unresolved transformation |
| --- | --- | --- |
| `root`, `pelvis` | synthetic scene root, `Hips` | Choose in-place versus root motion; apply trajectory once. |
| `spine`, `chest` | `Spine1`, `Spine2`, `Chest` | Collapse/recompose the source chain using rest-pose calibration. |
| `neck`, `head` | `Neck1`, `Neck2`, `Head` | Collapse neck chain; omit unsupported jaw/eyes. |
| `upper_arm.L/R`, `forearm.L/R`, `hand.L/R` | `Left/RightShoulder`, `Arm`, `ForeArm`, `Hand` | Fold shoulder motion into arm chain; no independent target fingers. |
| `thigh.L/R`, `shin.L/R`, `foot.L/R` | `Left/RightLeg`, `Shin`, `Foot` | Omit/handle toe channels and foot contacts explicitly. |

This table is **not a validated index map**. Names alone do not establish axes, offsets, bone lengths, bind pose or compatible local rotations. Measure pose/trajectory/foot-slide errors and visibly inspect wave, turn and path motion after conversion to the target GLB. The existing contract only references profile animation indices, so generated-asset attachment is a future integration-owner contract decision.

## One bounded alternate backend

The official resident path and unavailable local runtime justify checking one alternate: maintainer-owned [kimodo.cpp](https://github.com/localai-org/kimodo.cpp/tree/5679ff19ba0a522c0b0516e9a9d402fe1af2c027), commit `5679ff19ba0a522c0b0516e9a9d402fe1af2c027` (2026-09-17). It is a port of the same Kimodo model, not a separately validated motion provider. Its README describes CPU/Vulkan execution, 30-joint SOMA output, XYZW local quaternions and root translations, and skeleton-only GLB export. It says general constraint input, SOMA77 expansion and skinned mesh export are unfinished. Its documented build path is Linux with C++23, CMake 3.25+, Ninja and a pinned GGML submodule. The inspected README/CMake do not establish a tested macOS/Metal path. Do not transfer NVIDIA GPU timing to this Mac.

Exact converted candidates:

| Artifact | Revision | Update | Selected payload bytes |
| --- | --- | --- | --- |
| [F32 SOMA RP motion](https://huggingface.co/LocalAI-io/Kimodo-SOMA-RP-v1.1-GGML/tree/65f8b8ab34ee7524161cc87b20ae4cb4f5d3a12d) | `65f8b8ab34ee7524161cc87b20ae4cb4f5d3a12d` | 2026-08-26 | 1,133,166,784 |
| [Llama-derived text bundle](https://huggingface.co/LocalAI-io/Llama-3-Kimodo-GGML/tree/3e8d958803beaddb6011ac534f2be972e2710c7d) | `3e8d958803beaddb6011ac534f2be972e2710c7d` | 2026-09-17 | Q8: 8,142,058,752; Q4_K_M: 5,058,327,904; tokenizer: 7,295,054 |

The pinned manifests report exact SHA-256 values and name the same NVIDIA/Meta/McGill source revisions listed above. All 43 declared artifact sizes and 42 available LFS SHA-256 values match hub metadata. The small `final-norm.gguf` file has no hub SHA-256 in the response, so its publisher hash was not cross-checked. None of this verifies local model bytes. [Motion manifest](https://huggingface.co/LocalAI-io/Kimodo-SOMA-RP-v1.1-GGML/blob/65f8b8ab34ee7524161cc87b20ae4cb4f5d3a12d/MANIFEST.json), [text manifest](https://huggingface.co/LocalAI-io/Llama-3-Kimodo-GGML/blob/3e8d958803beaddb6011ac534f2be972e2710c7d/MANIFEST.json).

**Estimates only:** motion + tokenizer + Q8 text files total **8.645 GiB**; Q4_K_M totals **5.773 GiB**. Those payload sizes leave a possible 16 GiB CPU experiment, but they are not peak memory measurements or an operating budget. Graph buffers, tensor copies, activations, OS/other apps and quantization effects remain unknown. BF16 converted payloads alone total 15.197 GiB and leave little space. If later authorized, prefer a short, single-sample Q4_K_M CPU feasibility run with a process memory/time limit and an independently chosen quality control; the port's card labels this variant experimental. Do not install it or download it under this stage's authorization.

## Separate terms and authorization limit

This is an evidence inventory, **not legal approval**. Official [Kimodo code](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/LICENSE) and [C++ port code](https://github.com/localai-org/kimodo.cpp/blob/5679ff19ba0a522c0b0516e9a9d402fe1af2c027/LICENSE) carry Apache-2.0. The selected [NVIDIA weights](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1/blob/6c9233af1180b8151e3c4703477104af5dce9dd5/LICENSE) carry NVIDIA Open Model terms. The base encoder is gated under Meta Llama 3 Community terms; the converted [encoder instrument](https://huggingface.co/LocalAI-io/Llama-3-Kimodo-GGML/blob/3e8d958803beaddb6011ac534f2be972e2710c7d/LICENSE-META-LLAMA-3.txt) retains those terms. McGill adapter metadata identifies MIT. Conversion does not erase upstream terms. Public metadata availability is not evidence that the user has accepted gated terms or authorized weight use.

The Nvwa fixture has its own CC0 statement in `assets/fixtures/LICENSE.txt`. It contains authored actions. Neither that asset license nor code licenses establish rights for every optional SOMA/SMPL-X visualization asset, training dataset or redistributed model. No such third-party mesh/data was acquired. A target-rig adapter need not bundle the provider's display body; any later use still needs its own exact asset/terms review.

## Proposed future job boundary — no implementation

Keep inference outside Studio's realtime loop. A request should identify job ID, provider/code/checkpoint/encoder revisions and hashes, prompt, seed, fps/frame count, output skeleton and format, target fixture hash, units/axes/rest-pose convention and root-motion mode. Reject unavailable dependencies/weights before spawning; require local artifacts and an offline policy. Do not invoke upstream auto-download paths as a readiness test.

Use explicit queued/running/succeeded/failed/cancelled states. Preserve structured errors such as `inference_unavailable`, `resource_limit`, `output_schema_mismatch` and `retarget_failed`. A user cancellation should terminate only that owned worker, await its exit and keep partial files private. Failed/cancelled jobs must leave the current work and revision intact. Never substitute an authored preset.

Before admitting a result, validate bounded files and frame counts, finite arrays, joint names/order/hierarchy, 30/77 identity, matrix/quaternion conventions, units and sample times. Hash the genuine raw output and retain the actual process/run receipt. Normalize root motion exactly once, apply a separately validated target mapping and produce a playable target artifact plus provenance. Attach through a future atomic document command only after validation. A success flag or manifest assertion alone does not prove model generation or playback.

## Reproduction and actual evidence

From this worktree root:

```sh
python3 -B experiments/39-motion-provider-readiness/probe_local.py > .work/m12-motion-readiness/local-environment.json
python3 -B experiments/39-motion-provider-readiness/collect_sources.py > .work/m12-motion-readiness/collection-log.txt 2>&1
python3 -B experiments/39-motion-provider-readiness/analyze_schema.py > .work/m12-motion-readiness/schema-metadata.json
```

Create the private parent directory first if reproducing on another checkout. The collector reads 38 fixed public text/metadata URLs with 20-second timeouts, no retries, authentication or remote-code execution. It never requests weights. Each response must fit 2 MB and decode as UTF-8. The schema probe uses only stdlib parsing and checks every captured response hash before reading source as data.

Actual local probe: Apple M2 Pro, 16 GiB, macOS 27.0.1, `/opt/homebrew/bin/python3` 3.14.7. No target Python packages, model executables, CMake or Ninja were found in this interpreter/PATH. Known Hugging Face/torch/Kimodo roots are absent. This supersedes experiment 05's Python 3.9.5/PyTorch observation **only for this invocation**; other environments were not searched. No credentials, token files, broad environment dump or private filesystem scan was used.

Public evidence: [environment](evidence/environment.json), [source receipts](evidence/source-receipts.json), [schema/metadata](evidence/metadata-and-schema.json), [probe outcomes](evidence/probe-results.txt). Full raw public responses remain private at `.work/m12-motion-readiness/sources/` for root review. No processes, servers, GPU jobs, installs, model downloads or compiled artifacts remain owned by this worker. No Git mutation or external write was performed.

**VERIFIED —** 38 public text responses captured; all 38 hashes checked; pinned schemas count 30/77 joints, both official conversion call sites found, existing target skin counts 18 joints with unchanged fixture hash.

**NOT-RUN —** Genuine inference/output inspection, measured model memory/latency, Mac C++ build/runtime, retargeting, generated-action playback, cancellation behavior and distribution approval. Issue #12's actual-output and genuine-playback criteria remain open.
