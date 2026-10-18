# B1 authored continuous rehearsal

B1 motion uses the admitted MakeHuman body and sportsuit, its fitted53-bone rig and all positive final aggregate CPU influences. The two deterministic4-second clips are authored by Nvwa, not AI-generated. M2 action quality, appearance, cloth simulation, inverse kinematics, GPU4 and general imported motion remain outside this admission.

## Identity and commands

Work schema3 remains unchanged. Static profile `nvwa-mpfb-b1-v1` / `b1_cpu` version1 still has no clips or timeline. Motion profile `nvwa-mpfb-b1-motion-v1` / `b1_cpu` version2 uses the same thirteen authenticated raw files, asset ID and descriptor hash, with exactly two source clips. Changed clip definitions require a new profile identity. Unknown versions and altered canonical profiles are rejected.

`new-b1` keeps creating the static profile. `new-b1-motion <asset-root> <output.json>` authenticates the same asset before creating motion. Studio New B1 creates the latest explicit motion profile. Opening a static Work never upgrades it. Successful static Open clears all prior active clip/entry/seek/error state; Studio and Player also gate transport by the current profile capability. CLI apply/save remain offline metadata operations, and never control a running Studio.

Nonempty motion timeline exclusively owns all bone poses. Its stored diagnostic is dormant. Pause holds the sampled motion. `SetDiagnosticPose` atomically selects a static pose and clears the timeline; one Undo restores both. Empty timeline displays the stored diagnostic. Shape commands preserve the timeline, diagnostic and playback phase. Stage and scale only change presentation.

The source actions are:

| ID | Canonical bone-local peak rotation | Foot declaration |
| --- | --- | --- |
| `b1_arm_rehearsal_v1` | upperarm_l Z45 degrees; lowerarm_l Z75 degrees | Both planted |
| `b1_knee_flex_v1` | calf_l X+65 degrees; foot_l axis[0.9686015,-0.0100681,-0.2484144] -65 degrees | Right planted; left moving except neutral endpoints |

The knee action uses a fixed authored ankle counterrotation. Let `L` be the canonical rest rotation from calf to foot. The foot-local axis is `inverse(L) * X`, frozen above for this exact rig. The foot angle opposes the calf angle, so the foot keeps its rest orientation while the ankle follows the calf arc. Both admitted shape parameters retain this lower-leg rest frame. This does not solve a contact constraint or adjust grounding.

Pre-admission correction: the first unadmitted candidate used calf-only flex and actual sampled geometry dipped approximately20mm below the floor during early motion. The fixed foot counterrotation corrects the authored action. The profile and clip IDs remain unchanged by explicit root decision because no motion profile had been admitted or shipped; failed candidate evidence remains preserved. This exception does not change the rule that future changes to an admitted clip require a new profile identity.

Every peak angle is multiplied by `(1-cos(2*pi*t/4))/2`. Source time is clamped to[0,4], with exact neutral endpoints. All other bones reset to their fitted rest transforms on every sample. These declarations describe the authored action; measured foot quality is a separate acceptance result. No per-frame foot clamping or posed-minimum grounding occurs.

## Transport and fitting

Studio and Player share `Playback`. Runtime `Time` drives ordinary playback; exact probes use the same production systems with `TimeUpdateStrategy::ManualDuration` or `Playback.seek_request`. Timeline array order is storage order; start times define the sequence. Gaps hold the preceding endpoint, speed multiplies source time, and looping wraps source time. A start-zero single loop is an indefinite source-phase preview. Other sequences stop at their finite endpoint and Replay restarts at0. Nonfinite seek is rejected without changing the sampled pose.

Open resets a successfully admitted motion Work to0 and paused. Pending or rejected Open leaves committed playback and history active. Shape fitting freezes automatic advancement and retains the current cursor and live Play/Pause intent. The latest finite Seek/Restart request stays pending until a fitted rig successfully displays that sample. Superseded fits cannot consume it. Restart is the established explicit seek0 plus Play intent; a later Pause while fitting wins. Timeline changes reset the cursor; concurrent explicit seek wins.

A fitted shape caches canonical rig frames, fitted morph arrays, source mappings, raw and normalized full influences, visible indices and fitted-rest stage placement. Each changed sample updates actual local bones, propagates the Bevy hierarchy, reads actual bones, evaluates CPU skin and updates existing display mesh handles. A cheap shared structural guard verifies exact display-to-mesh bindings, actual bone entities/transforms/hierarchy and fitted part/index coverage before clock advancement, pose application, publication, readiness and readback. Both parts validate before either upload. Failed frames retain both last displayed buffers, pause advancement and reject readback until a consistent frame recovers.

## Explicit production readback

`nvwa_runtime::b1_frame_snapshot(&World) -> Result<serde_json::Value, String>` reads a successful motion-profile frame after publication. It rejects unavailable, pending-shape, failed or inconsistent states. The complete visible Work, resolved transport and actual display transforms must match the last normal publication. A command or queued seek before the next publication cannot relabel retained geometry. Paused scale/stage changes acquire their new binding after propagation without re-skinning unchanged local geometry. It checks actual ECS bone matrices against the published frame and actual uploaded mesh buffers against full-positive skin from those bones. Full geometry readback is opt-in; it is not part of the ordinary UI status tick.

Top-level schema version1 fields:

- `backend`, `profile_id`, `asset_id`, `generation`, `revision`, `parameters`, `diagnostic_pose`, `mode` (`motion` or `diagnostic`), `character_entity`.
- `sample`: `serial`, `clip_id`, `timeline_id`, `position_seconds`, `source_seconds`, `playing`, `completed`. Loop position4 resolves to source0; a finite nonloop endpoint4 resolves to source4.
- `bones`: all53 existing serialized `BoneFrame` rows, including `name`, `parent`, `rest`, `posed`, `inverse_bind`, `local_rest`, `local_posed`, `skin`, `canonical_rest`, `canonical_posed`, `frame_gauge`.
- `parts`: body and garment rows with `name`, `display_entity`, `mesh_handle`, `source_ids`, uploaded `indices`, `positions`, `normals`, `tangents`, fitted `rest_positions`, `rest_normals`, raw pre-normalization `full_joint_influences`, `model_to_world`, `display_transform`.
- `contacts`: `left` and `right` are `planted`/`moving` for authored motion, or `diagnostic` in static diagnostic mode.

Matrices are column-major. Positions and fitted rests are source model-local metres. `model_to_world` is the source skeleton global transform retained by the existing adapter. `display_transform` is the actual displayed mesh GlobalTransform, including source-root placement and scale. To obtain stage/world positions apply `display_transform` once to model-local positions; do not apply `model_to_world` again.

CPU matrix/mesh tests and exact sampled probes are separate from visible native/Web playback evidence. Historical experiments53–59 remain controls and are not regenerated. See the separately owned experiment60 acceptance report for measured joint, contact and garment results and explicit limits.
