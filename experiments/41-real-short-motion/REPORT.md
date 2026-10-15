# 41 — Genuine short-motion CPU preflight

**Outcome: a local CPU executable is built and its guard is exercised. Genuine generation remains NOT-RUN pending explicit approval for three model artifacts and one bounded run.** No model, encoder, tokenizer, training data, display body, cloud inference, or paid API was acquired or executed. This directory does not change Studio, the document schema, fixture assets, dependencies, or Cargo files.

Observed 2026-10-15 on Apple M2 Pro, 16 GiB, macOS 27.0.1. This refreshes experiment 39's observations for this exact invocation. The current Python is 3.14.7 with no Kimodo, torch, transformers, LLM2Vec, MLX, or NumPy. `kmd-generate`, CMake and Ninja were initially absent from PATH. The five named HF/torch/Kimodo cache/runtime roots were absent and no explicit cache roots were configured. No disk-wide, private-data, token, or credential search was performed. See [environment](evidence/environment.json).

## Preparation completed

The pinned [kimodo.cpp source](https://github.com/localai-org/kimodo.cpp/tree/5679ff19ba0a522c0b0516e9a9d402fe1af2c027), [motion metadata](https://huggingface.co/LocalAI-io/Kimodo-SOMA-RP-v1.1-GGML/tree/65f8b8ab34ee7524161cc87b20ae4cb4f5d3a12d), and [text metadata](https://huggingface.co/LocalAI-io/Llama-3-Kimodo-GGML/tree/3e8d958803beaddb6011ac534f2be972e2710c7d) still matched experiment 39's revisions when refreshed through hosted web research and bounded public text requests. No assumption of current weights was carried forward.

With the parent's separate setup authorization, `setup_cpu.py` fetched 168 source-text files totaling **5,870,148 bytes**. Every file matched its exact pinned Git blob SHA-1; SHA-256 receipts are also retained. Each source response was at most 2 MiB and decoded as UTF-8. Selected sources comprise Kimodo code/headers/test source and GGML code/CPU source/headers/CMake support. No test fixtures or model payloads were selected. GGML is pinned to `8c63e70982c95ceb862e3a1073a2c1beef75d60a`. [Source receipts](evidence/setup-source-receipts.json)

The approved private build tool is [Kitware CMake 3.31.12 macOS universal](https://github.com/Kitware/CMake/releases/tag/v3.31.12), **79,954,716 bytes**, SHA-256 `799af7fd545db9bf1b9cfe72f8095880e727a2d4e0df0e3dffc3bc7b95c2d3b0`. Its archive was checked before extraction into `.work/m2-provider/tools/`. Existing Apple clang 21 and Make 3.81 were used. An own five-line C++23 `std::expected`/`std::format` probe compiled and ran successfully. No machine-wide install or PATH change occurred. [Tool receipt](evidence/setup-tool-receipt.json), [compiler probe](evidence/cxx23-probe.json)

The build-hook audit found an optional GGML KleidiAI download. It was explicitly disabled. `FETCHCONTENT_FULLY_DISCONNECTED=ON` was also supplied; CMake reported this variable unused because the guarded download branch was not entered. Configure and build both ran inside macOS `sandbox-exec` with `(deny network*)`. The audited hooks otherwise inspect compiler/linker capabilities or Git metadata; `GIT_EXE` was explicitly empty to prevent ancestor-repository metadata leakage. [Hook inventory](evidence/setup-build-hooks.json)

Actual configure **4.078 s**, build **17.104 s**, both exit 0. The build targeted only `kmd-generate`, with at most two jobs and a 600-second owned-group deadline. CPU was enabled; Metal, Vulkan, BLAS and other accelerator backends, OpenMP and KleidiAI were disabled. System Accelerate remained enabled within the CPU library. No GPU inference or GPU build was used. [Actual commands](evidence/setup-build-receipts.json), [configured flags](evidence/build-flags.txt)

Built executable: `.work/m2-provider/runtime/build-cpu/kmd-generate`, **279,632 bytes**, SHA-256 `55b5c74fb7ab8c83d1560476eb2b9a29e184cbc7020181f3d6eeef44840e9f7d`. Its three private GGML dylib hashes are [recorded separately](evidence/built-library-hashes.json). `--help` was source-checked to return usage before model loading, then actually launched offline: expected **exit 2**, **0.537 s**, no model path supplied. This proves executable startup and loading of its CPU libraries; model loading and inference remain NOT-RUN. [Smoke receipt](evidence/help-receipt.json), [linked libraries](evidence/linked-libraries.txt)

## Exact proposed model acquisition — not executed

Three publisher hashes and sizes match current Hugging Face LFS metadata and the pinned manifests. These are remote metadata checks, not local-weight checks. [Machine-readable list and exact download URLs](proposal.json)

| Artifact | Repository revision | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| [F32 motion](https://huggingface.co/LocalAI-io/Kimodo-SOMA-RP-v1.1-GGML/resolve/65f8b8ab34ee7524161cc87b20ae4cb4f5d3a12d/models/kimodo-soma-rp-v1.1-f32.gguf) | `65f8b8ab34ee7524161cc87b20ae4cb4f5d3a12d` | 1,133,166,784 | `3bf1229f4c1eff1d28f5196a854113da2df9a11a5e21c60694630903bf948ee4` |
| [Q4_K_M text encoder](https://huggingface.co/LocalAI-io/Llama-3-Kimodo-GGML/resolve/3e8d958803beaddb6011ac534f2be972e2710c7d/Llama-3-Kimodo-Q4_K_M.gguf) | `3e8d958803beaddb6011ac534f2be972e2710c7d` | 5,058,327,904 | `c06f2cb6a7615e949bcbb5b582ad35a191338b68b5a51abe17d259ebe574c005` |
| [Shared tokenizer](https://huggingface.co/LocalAI-io/Llama-3-Kimodo-GGML/resolve/3e8d958803beaddb6011ac534f2be972e2710c7d/tokenizer.gguf) | `3e8d958803beaddb6011ac534f2be972e2710c7d` | 7,295,054 | `81614aca62a98846c02b72cc2e5378e5bdce8b4d507b88f96eb1faa90dae607e` |

**Total: 6,198,789,742 bytes = 6.199 decimal GB = 5.773 GiB.** This is disk/network payload size, not a peak-memory estimate. The publisher calls Q4_K_M its preferred low-bit experiment. Quality, peak memory and completion time on this Mac remain unknown. No claim follows from the successful build that a model run will finish under the proposed limits.

Code terms: [Apache-2.0 for kimodo.cpp](https://github.com/localai-org/kimodo.cpp/blob/5679ff19ba0a522c0b0516e9a9d402fe1af2c027/LICENSE); [MIT for GGML](https://github.com/ggml-org/ggml/blob/8c63e70982c95ceb862e3a1073a2c1beef75d60a/LICENSE). Motion weights retain the [NVIDIA Open Model License](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1/blob/6c9233af1180b8151e3c4703477104af5dce9dd5/LICENSE). The encoder retains [Meta Llama 3 Community terms](https://huggingface.co/LocalAI-io/Llama-3-Kimodo-GGML/blob/3e8d958803beaddb6011ac534f2be972e2710c7d/LICENSE-META-LLAMA-3.txt), including its acceptable-use obligations; McGill adapters retain MIT. Conversion supplies no new rights. The converted repositories currently report `gated=false`; this does not establish the user's legal approval or prior acceptance of upstream gated terms. No credentials or acceptance state were inspected. Acquisition must stop on access/terms gates or HTTP 401/403; no login, acceptance, token lookup or alternate source is authorized. Redistribution is outside this experiment.

## One proposed run and actual guard proof

Prompt: `A person stands in place and waves their right hand.` Seed **42**, **90 frames**, **30 fps**, **25 diffusion steps**, both CFG values **2.0**. Nominal frame budget is 3 seconds; first-to-last sampled time is **89/30 = 2.9666666667 seconds**. No extra endpoint is synthesized.

After explicit human approval and independent review, `acquire_models.py` can stream only those three exact files into `.work/m2-provider/approved-models/`, checking size and SHA-256 before rename. Its approval flag records permission obtained outside the script; a flag alone is not authorization. It never installs packages or accepts terms. No acquisition invocation has been run.

`run_guard.py` defaults to describing the proposal. Its separately gated run uses exact local files and checks model, binary and private dylib hashes before launch. Invocation prepared in code:

```text
kmd-generate <private>/approved-models/kimodo-soma-rp-v1.1-f32.gguf <private>/approved-models/Llama-3-Kimodo-Q4_K_M.gguf <owned-run>/prompt.txt 90 25 42 <owned-run>/raw
```

The command is wrapped by macOS network denial. Its minimal environment contains CPU/backend limits and offline flags, with no inherited account tokens or proxies. `KIMODO_THREADS=4`, `KIMODO_TEXT_LAYER_CHUNK=1`, `VECLIB_MAXIMUM_THREADS=4`. The C++ source reads local GGUF paths; upstream downloader scripts are never called during generation. The owned process group is stopped at 600 seconds or **7 GiB sampled group RSS**, with SIGTERM followed by SIGKILL after 0.3 seconds if needed. User cancellation follows the same owned-group path. It retains process, prompt, source/model/runtime identity and raw-output hashes; failures leave private partial files and do not produce a normalized success.

The 600-second value is a monitoring abort threshold. Bounded process inspection and teardown can add latency; this is not an OS-enforced hard runtime deadline.

**8 GiB is a planning ceiling, not a proven hard cap.** RSS is sampled every 100 ms; the 7 GiB stop gives 1 GiB of headroom, but allocations between samples can overshoot. No kernel-enforced RSS cap is claimed. If a strict never-exceed-8-GiB condition is required, this Mac watchdog does not establish it, and inference must stay blocked.

Five actual low-cost controls exercise the same guard: denied loopback connection (`EPERM`), deadline termination, synthetic 32 MiB allocation crossing a 24 MiB test threshold, termination of a two-member process group, and SIGKILL escalation for a child that ignores SIGTERM. All owned groups were verified absent afterward. The last control run took approximately 1.3 seconds total. These are guard/control results, not model resource or cancellation measurements. [Actual receipts](evidence/guard-controls.json)

## R2 pre-run corrections

Independent R2 review held the initial run proposal for two concrete gaps. Cleanup could lose escalation and its receipt if process inspection failed during teardown. The C++ native-float prerequisite was also stated but unenforced. Both are corrected within this experiment; original build and initial control evidence remain unchanged.

Teardown now signals the owned group even after its leader exits. Inspection and wait failures are caught and recorded. Unavailable inspection triggers KILL independently, with finite waits and a final bounded inspection. Missing inspection never becomes verified absence. Real SIGINT/SIGTERM are deferred during teardown and receipt persistence. Persistence is always attempted; an I/O failure is explicitly reported to stderr instead of being treated as a saved receipt.

Three new actual process controls exercise the repaired seam. Repeated inspection failure with a TERM-ignoring child produces **SIGKILL, leader exit -9, a durable receipt, `cleanup_unconfirmed`, and `owned_group_exit_verified=false`**. An independent post-control inspection then confirms absence without changing the receipt's uncertainty. A leader that exits while its TERM-ignoring descendant remains still triggers group KILL and verified absence. Actual SIGTERM delivered to the guard during cleanup is deferred; KILL/reaping/receipt finish with `cancelled`. [Failure receipts](evidence/failure-controls.json)

All five original controls were also rerun against the repaired guard, with all owned groups absent afterward. [R2 control rerun](evidence/guard-controls-r2.json)

The model-free [C++ format probe](float_probe.cpp) uses the **exact provider compiler and compile flags** from the retained CMake build. Static assertions require 8-bit bytes, four-byte IEC559 binary32, radix 2, 24 significand bits, the binary32 exponent range, little-endian representation and the expected 1.0 bit pattern. It then writes a native `float` using the same `fwrite` byte convention as the provider's native write. Compilation succeeded in **0.855 seconds**; execution emitted exactly `0000803f`. Probe SHA-256 is `263aaf8dc085b2b907886aca3a0715b5a10667b0fd14ac2fff272bdd73885f2d`. [Compiler/runtime-bound receipt](evidence/float-prerequisite.json)

`float_prerequisite.py` binds this proof to the current compiler bytes, compiler configuration, flags, CMake cache, unchanged provider binary, all three private dylibs, probe source and probe executable. The actual run entrypoint requires that identity and replays the tiny offline probe **before any model/inference path**. Controls reject missing and stale-runtime receipts, and exercise the real run entrypoint with a failing prerequisite to prove no provider launch is reached. No model files were used or created. This proves the native-float prerequisite for this exact build; actual model numeric/axis admission remains separate.

### R2 BSD `ps` classification follow-up

A further R2 control found that BSD `ps` uses exit 1 for both a clean no-match and an invalid-group diagnostic. The earlier `group_rss` ignored stderr and could turn the latter into a false group-absence claim. This specific defect held the previous freeze `6884ad95d6b415a6299637c2b067718cc8a080fab993a5a9b9a7c1c7f6a6a897` from run approval.

`group_rss` now rejects diagnostic stderr at **every** exit status. Exit 1 means clean no-match only when stdout and stderr are both exactly empty. Exit 0 requires nonempty, well-formed records with positive PIDs, the requested positive process group, nonnegative RSS and no duplicate PIDs. Other statuses and malformed/unexpected records remain inspection uncertainty and enter the existing KILL/receipt path.

The regression control first captured actual BSD responses: `ps -g 99999` returned exit 1 and both streams empty; `ps -g 2147483647` returned exit 1, empty stdout and `ps: process group too large: 2147483647\n` on stderr. It then injected that exact diagnostic response at the production `subprocess.run` inspection seam after an actual owned TERM-ignoring child became ready. This is an error-class injection, not a claim that the child's real `ps` query naturally failed.

**Red:** the prior implementation falsely reported verified group absence and left the child alive; independent test cleanup KILLed and reaped it. **Green:** the fixed implementation sends KILL, reaps exit -9, persists the matching receipt with `cleanup_unconfirmed` and `owned_group_exit_verified=false`, and independent real `ps` confirms absence. No emergency test cleanup is needed. All 13 response-class controls pass, including clean no-match, valid exit-0 records, diagnostic stderr at exits 0 and 1, exit-1 records, empty successful output, and malformed/unowned/negative/duplicate records. [Actual classification/control evidence](evidence/ps-classification-controls.json), [red/green receipts](evidence/ps-red-green.json)

All eight existing actual child/network/cleanup controls were rerun against this inspection fix. Their earlier receipts remain unchanged; new [five-control](evidence/guard-controls-ps-r2.json) and [three-failure-control](evidence/failure-controls-ps-r2.json) receipts record the rerun. No compiler, provider build, model, or download was used for this repair.

## Raw format and normalization handoff

Pinned [`src/generate.cpp`](https://github.com/localai-org/kimodo.cpp/blob/5679ff19ba0a522c0b0516e9a9d402fe1af2c027/src/generate.cpp) writes two **host-native float** streams, without a self-describing header, JSON or NPZ:

| File | Expected shape | Exact bytes for this run |
| --- | --- | ---: |
| `root_positions.f32` | `[90,3]` | 1,080 |
| `local_rotations_xyzw.f32` | `[90,30,4]` | 43,200 |

The enforced same-compiler C++ probe above establishes this build's native little-endian IEC559 binary32 representation. Model output itself is NOT-RUN. CLI success stdout must be exactly `generated 90 frames with 30 joints\n` with exit 0. Caught exceptions write stderr and exit 1. Files are created sequentially with truncating writes; a failed/cancelled run can leave one or both incomplete files. Require both exact sizes and hashes plus process completion. Do not infer success from file presence.

The parsed [source-skeleton metadata](source-skeleton.json) records unique ordered 30-joint names, parents, parent-local offsets, identity local rest rotations and unit scales, derived from the pinned [`skeleton.hpp`](https://github.com/localai-org/kimodo.cpp/blob/5679ff19ba0a522c0b0516e9a9d402fe1af2c027/src/skeleton.hpp). It contains **no motion samples**. The C++ port returns SOMA30, not the official API's expanded SOMA77. No hand expansion is assumed.

Official [format documentation](https://github.com/nv-tlabs/kimodo/blob/58e781898b3d7e328a676a75d3e338c45dce3ad9/docs/source/user_guide/output_formats.md) establishes meters and Kimodo Y-up/+Z-forward. The C++ decoder directly emits those position components and parent-relative rotations. The [GLB exporter](https://github.com/localai-org/kimodo.cpp/blob/5679ff19ba0a522c0b0516e9a9d402fe1af2c027/scripts/export_glb.py) copies them unchanged into glTF, which indicates right-handed identity-basis intent. **Source handedness remains UNKNOWN for admission**: no signed-axis control or actual generated orientation has been verified. Do not label it compatible by assumption.

The exporter also uses a 0.988 m root rest height, while C++ skeleton offsets have zero at Hips. Normalization must use an explicit rest convention. Raw root trajectory replaces the Hips translation exactly once; do not add the exporter height or apply the trajectory again to a scene root. Sample times are `i/30`; validate finite, strictly increasing values and finite/nondegenerate local XYZW rotations. Preserve raw hashes/provenance separately. Actual normalization, target retargeting and genuine playback require their own evidence and remain NOT-RUN. Authored controls stay labelled authored.

## Reproduction and retained state

```sh
python3 -B experiments/41-real-short-motion/collect_metadata.py
python3 -B experiments/41-real-short-motion/analyze_preflight.py
python3 -B experiments/41-real-short-motion/setup_cpu.py fetch
python3 -B experiments/41-real-short-motion/setup_cpu.py audit
# Review hooks before authorizing or replaying build.
python3 -B experiments/41-real-short-motion/setup_cpu.py build
python3 -B experiments/41-real-short-motion/float_prerequisite.py --prepare
python3 -B experiments/41-real-short-motion/float_prerequisite.py
python3 -B experiments/41-real-short-motion/run_guard.py --controls
python3 -B experiments/41-real-short-motion/test_guard_failures.py
python3 -B experiments/41-real-short-motion/test_ps_classification.py
```

These commands are scoped operations, not blanket authorization for a future replay. Acquisition and genuine-run commands are deliberately omitted until explicit permission. The fixed text inventory and 40 response hashes are [retained](evidence/source-receipts.json); `analyze_preflight.py` checked all 40 and all three selected metadata hashes/sizes.

Parent owns retained `.work/m2-provider/` source, tool, build and control evidence, approximately **339 MiB**. Both compiler tokens were released. No owned build/control/provider process, server or GPU job remains. No model files exist in the proposed acquisition directory. No Git/GitHub writes were made. This model-free state is intentionally retained for independent review and a possible approved run.

**Permission draft:** Approve downloading the three pinned files above (6.199 GB) under their linked NVIDIA/Meta terms, then one offline CPU generation attempt of the stated prompt/seed, at most 10 minutes, stopped at 7 GiB sampled RSS toward an 8 GiB planning ceiling. This may yield no sample if resources or limits fail. No paid compute, cloud service, distribution or physical-human test is included.

VERIFIED — 40 public text hashes; three remote artifact hashes/sizes; 30-joint source metadata; exact private CPU build/startup; eight rerun actual guard/cleanup controls; 13 BSD ps response classifications plus actual-child red/green proof; compiler/runtime-bound C++ native-float proof and launch-prerequisite rejection controls.

NOT-RUN — Model acquisition/loading/inference, actual peak memory/latency, raw byte/schema/orientation admission, normalized genuine motion, retargeting, generated playback and physical-human assessment.
