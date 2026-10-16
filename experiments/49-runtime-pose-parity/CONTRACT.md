# Same-frame runtime pose investigation

Scope: diagnose the existing experiment-48 quality HOLD. No inference,
downloads, retargeting changes, asset replacement, or performance claim.
Experiments 41–48 and the original character remain immutable.

Inputs are experiment 48's retained Work/profile/GLB and genuine experiment-44
sample. Capture clip `genuine44_calibrated47` at source key indices
`[0, 15, 30, 45, 60, 75, 89]`, with the exact binary32 GLB key time.
All 90 keys may additionally be tested offline. Do not conflate nominal
3 seconds with the final key at 89/30.

For each actual native/Web sample record the capture schedule (after Bevy
animation evaluation and global-transform propagation), frame counter,
requested and observed clip/time, Work identity/revision, node identity and
parent, local translation/rotation/scale, global matrix, CharacterRoot and
all GLB ancestors needed to interpret the skin's joints. Record actual
skinned mesh/skin bindings when available. Missing state must fail rather
than silently skip. Never copy expected values into the runtime collector.

Use the existing shared Studio/runtime pipeline in a separately launched,
bounded diagnostic harness. Prefer an isolated experiment crate; no default
product CLI/query surface or root dependency/lock changes. Probe-specific
code may read public runtime state. Any necessary product seam must be small,
explicit, separately reviewed, and use production scheduling.

Runtime owner: probe crate, actual native/Web execution readiness, runtime
capture schema (`probe/SCHEMA.md`), and final experiment report. Offline helper:
`offline/` only, independent GLB evaluator, raw/expected comparisons and tests.
Root owns this contract, shared manifests/CI/roadmap, integration and review.
No simultaneous edits to shared files. The offline helper waits for the
runtime schema before implementing the actual-capture adapter.

Compare quaternion signs equivalently and full hierarchical matrices without
normalizing away axis/root/scale errors. Separate local/global bone agreement
from skin deformation, body intersections, anatomical/semantic quality and
official decoder parity. Retain negative controls for wrong time/clip, missing
bones, root application and perturbed pose. State each threshold and maximum
error. Matching bones does not make the motion good.

Native and Web compilation, launch, pose capture, visual checks and comparison
are separate evidence gates. Keep all timeouts bounded. At most two heavy
builds and one graphics workflow globally; build/execution slots are granted
by root. Preserve the user's existing Alpha app/tab/server and saved Work.
No new physical-human trial is authorized by this experiment.
