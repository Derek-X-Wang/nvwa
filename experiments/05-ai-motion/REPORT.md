# 05 — Genuine text-to-motion readiness and preset artifact import

## Outcome

**INCONCLUSIVE for genuine local AI motion generation. True inference NOT-RUN.**
Kimodo is a real text-to-motion candidate, but this experiment found no usable
installed Kimodo runtime and authorized weights in the checked local locations.
No prompt was sent to a model, no API or paid service was called, no weights or
packages were downloaded, and no GPU inference/build was attempted.

**Adopt only the isolated file-import boundary as an experiment.** Nine Python CPU
tests pass against a frozen existing authored wave preset. That preset is expressly
not AI motion. Runtime, mainline core, dependencies, and Cargo.lock are unchanged.

## Question, hypothesis, controls, and exits

Question: Can this M2 machine generate genuine text-conditioned motion from an
available local model without expanding M0 dependencies or silently using presets?

Hypothesis: A model job can remain outside the editor and return a validated,
provenance-labelled file. If inference is unavailable, it must report that status
without turning a preset into an apparent model result.

Control: Freeze only the named manually authored wave animation from the real Nvwa
humanoid GLB. Preserve its actual skinned geometry and binary animation samples.
Import that frozen file through a request/manifest boundary. No novel motion is
created; the prompt string is bookkeeping and prompt alignment is unmeasured.

Acceptance for real generation would require an installed compatible backend,
authorized exact code/weight revisions and license records, no unapproved download,
measured resource use, actual model execution, finite valid output, and separate
retargeting/visual inspection. None of those inference claims is met here.

Acceptance for the limited boundary requires successful preset import and rejection
of changed hashes, malformed/missing assets, traversal/symlink escape, unknown and
duplicate JSON fields, invalid durations/seeds, wrong job/name, falsely AI-labelled
presets, and a model job that would otherwise fall back silently.

Exit without generation when local runtime or weights are missing; do not install,
download, accept terms, inspect credentials, or consume network/paid inference.
Stop on schema, integrity, reference, or duration error. Keep this optional work
out of the M0 build and ship path. This is not a retargeter or motion framework.

## Primary-source research

Research checked on 2026-10-10. Sources are the authors' repositories/model cards
and owning license documents, rather than third-party summaries.

- NVIDIA's official Kimodo repository describes text-conditioned kinematic motion
  generation. It reports automatic weight downloads when generation is started,
  about 17 GB GPU memory for the complete default path, and primarily Linux/NVIDIA
  testing. It identifies SOMA 77-joint output in its current changelog. The native
  Nvwa rig has 18 joints, so direct import would need a separate mapping/conversion
  experiment. [Official repository](https://github.com/nv-tlabs/kimodo)
- Official code is Apache-2.0. Model checkpoints are separate artifacts with their
  own terms. [Owning code license](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/LICENSE)
- Selected candidate `nvidia/Kimodo-SOMA-RP-v1.1` is labelled NVIDIA Open Model
  License. Its card lists Linux/Windows and NVIDIA GPU architectures; it does not
  establish M2 support. The card still describes 30-joint tensors while the repo
  changelog says 77 joints. Treat this as documentation drift and inspect the
  actual checkpoint/config/output before writing an adapter.
  [Owning model card](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.1)
- The NVIDIA Open Model License permits commercial use subject to its conditions,
  requires license/notice when distributing models, and disclaims ownership of
  outputs. This does not license every third-party component or alternative
  Kimodo checkpoint. [Owning model license](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/)
- The official installation path uses the gated Meta-Llama-3-8B-Instruct text
  encoder, requires model access and an HF token, and suggests Python 3.10.
  No token/access was inspected or obtained here.
  [Official installation](https://research.nvidia.com/labs/sil/projects/kimodo/docs/getting_started/installation.html)
- Meta-Llama-3-8B-Instruct has its own Meta Llama 3 Community License and gated
  access involving contact information. This experiment did not accept terms or
  submit information. [Owning encoder model/license](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct)
- An independent Kimodo Motion add-on author documents an Apple Silicon MPS port,
  Python 3.10–3.13, Blender 5.0.1+, roughly 25–50 GB disk and 32 GB unified memory
  recommended. This is the port author's claim, not verified M2 performance here.
  Its add-on README lists GPL-3.0-or-later add-on code, Apache-2.0 Kimodo fork code,
  and separate NVIDIA/Meta weight terms.
  [Author's Mac requirements](https://github.com/atticus-lv/kimodo_motion/blob/main/INSTALL_EN.md),
  [author's component license table](https://github.com/atticus-lv/kimodo_motion/blob/main/README.md)
- An independent MLX port describes MIT code and Metal-only execution, retaining
  NVIDIA/Meta/LocalAI weight terms. Its published measurements use M4 Max with
  64 GB, not M2. The author says the resident 15 GB encoder is unsuitable on a
  16 GB Mac. These measurements were not reproduced. This port is not an available
  local backend in this experiment.
  [Port author's implementation/evidence](https://github.com/NomaDamas/kimodo-mlx)

Inference: the current 16 GiB M2 Pro is not a justified default for the documented
resident MLX path. A streaming/CPU or different backend might be feasible, but
feasibility, peak memory, latency, and M2 output quality remain unmeasured. Do not
claim that Metal capability alone makes Kimodo ready.

## Observed local environment

`local-environment.json` records the actual read-only probe:

- Apple M2 Pro, arm64, 17,179,869,184 bytes (16 GiB) memory.
- The invoked `python3` is 3.9.5. PyTorch 2.7.1 is installed; MPS reports built and
  available. No model tensor computation was performed.
- `kimodo`, `transformers`, `llm2vec`, and `mlx` are absent from this interpreter.
  `kimodo_gen` and `kmd-generate` executables were not found. Blender is present.
- Default Hugging Face and torch checkpoint locations, and the usual Kimodo runtime
  directories, do not exist. The probe also checks explicit non-secret cache-path
  variables. This is a bounded location check, not a claim about every disk file
  or every other Python environment. No authorized candidate weights were found.

## Standalone boundary and actual evidence

`artifact.py` exposes `parse_job(JSON)` and `import_artifact(job, manifestJSON, root)`.
The schema records job ID, prompt, duration, seed, backend, artifact hash, named
animation, source hash, license and explicit origin. `kimodo_local` reports
`inference_unavailable` with NOT-RUN; it never executes a command or substitutes
motion. `preset_import` permits only `source_kind=authored_preset`,
`ai_generated=false`, and `model_id=null`.

Import validates bounded strict JSON, provenance consistency, root containment,
file size/hash, GLB framing, named animation/node references, time arrays, finite
TRS samples, nondegenerate quaternion/scale values and actual duration. The result
reports `prompt_alignment_measured=false`. These checks are deliberately smaller
than a full glTF validator and do not prove rendering or model provenance.

Actual commands from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/05-ai-motion/probe_environment.py > experiments/05-ai-motion/local-environment.json
PYTHONDONTWRITEBYTECODE=1 python3 experiments/05-ai-motion/freeze_fixture.py > experiments/05-ai-motion/freeze-output.json
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s experiments/05-ai-motion -p 'test_*.py' -v > experiments/05-ai-motion/test-output.txt 2>&1
```

Final CPU test run: **9 tests passed, 0 failed, 0.034 seconds**. Raw output is retained
in `test-output.txt`. A direct import returned the result in `import-result.json`:
job `preset-wave-1`, state `imported`, animation `wave`, one skin, `ai_generated=false`
and actual accessor duration **3.0416667461395264 seconds**.

The first import check rejected the assumed nominal 3-second duration. The freeze
script now reads actual keyframe times rather than rounding duration. No mainline
profile change was made. Original source bytes are asserted unchanged by freezing.

## Hashes and artifacts

Original source SHA-256:

```text
f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6
```

Frozen authored preset SHA-256:

```text
f651ae2cb6550a2fefd4f44730ab69d13aebe585eb2546b8d46845928ac6d627
```

- `authored-wave.glb`, `artifact-manifest.json`, `job.json`: frozen authored control.
- `SOURCE-LICENSE.txt`: original fixture CC0 license, preserved without modification.
- `artifact.py`, `test_artifact.py`: isolated import boundary and regression tests.
- `freeze_fixture.py`, `freeze-output.json`: reproducible fixture extraction/provenance.
- `probe_environment.py`, `local-environment.json`: reproducible local readiness probe.
- `test-output.txt`, `import-result.json`: actual CPU test/import evidence.

## Decision and remaining uncertainty

Keep genuine AI inference blocked for this bounded run. Keep the import experiment
as a reviewable candidate for a later offline job boundary. Do not label the frozen
wave as generated, prompt-conditioned, model-tested, or AI motion. Source/hash
metadata is a provenance assertion and must be backed by a future actual run;
a hash alone cannot prove how motion was created.

A genuine follow-up needs an exact authorized local model/runtime, reconciled
output schema, measured M2 resource behavior, separate Nvwa joint mapping and visual
playback. Nothing in this experiment blocks or changes M0. Test temporary folders
were created inside this experiment and automatically removed; no model process,
server, download, install, GPU job or compiled artifact was created.

VERIFIED — Nine Python CPU import tests passed with frozen authored-wave bytes.
NOT-RUN — Genuine model inference, M2 model performance, retargeting and playback.
