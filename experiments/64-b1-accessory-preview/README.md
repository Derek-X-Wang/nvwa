# Live accessory preview (experiment64)

Standalone wrapper of unchanged nvwa_studio::build_app(). Baseline, skin, and skin+eyes+hair use the same actual B1 body, shape parameters and authored motion. Appearance is temporary and NOT saved. #3 blocked, #4 gap, clothes/M2 HOLD remain. No gaze, physics or MPFB shader reproduction claim. Authored head motion is NOT-RUN; current clips do not prove head motion.

Native and Web have an egui experiment window with mode, Full/Face/Back observation camera, shape/sample/play/pause/report controls. Web also provides accessible DOM controls and `window.b1_64`. The camera presets reuse production StageViewOverride; they do not mutate Work.

Strict interface (same queue in all cases):

```json
{"request_id":"accessory-1","action":"accessories"}
{"request_id":"sample-1","action":"sample","clip_id":"b1_arm_rehearsal_v1","seconds":2,"torso_length":0,"jaw_drop":0.5}
```

Actions: baseline, skin, accessories, report, sample, play, pause, view_full, view_face, view_back. Only sample takes extra keys. Torso[-1,1], jaw[0,1], seconds[0,4]. Clips: b1_arm_rehearsal_v1 / b1_knee_flex_v1. Unknown keys/actions/clips and malformed values reject. Reports are invalidated by real Work/transport changes. Retry a valid request after a rejection.

Native env: B1_64_COMMAND_FILE points to a JSON file; change bytes to send a new request. If an explicitly configured channel cannot be read or decoded, proof is invalidated and a recoverable error is shown. Restore readable valid JSON to recover. GUI use without this environment variable is normal. Optional B1_64_REPORT_FILE and B1_64_FRAME_FILE are atomically replaced after observation; stale full frames are removed. Caller owns these exact paths and their `.64-tmp` siblings. Wasm exports `b1_64_command(JSON_string)`, `b1_64_report()`, `b1_64_frame()`.

Wait for `phase=captured` and matching request_id. Full frame has `snapshot` (fresh verified production body/garment/bones) and `appearance.accessory_runtime` (actual rest/full weights/CPU upload arrays/UV/indices/material/placement). Each captured frame binds generation/revision/sample serial. desired and applied use the same explicit baseline/skin/skin+eyes+hair identity. Perframe live streaming reads actual53 bone GlobalTransforms via public adapter bone_frames; it does not serialize/recompute the whole body or full observation arrays each frame. Full capture re-reads the current material flags, bound image dimensions/format and pixel hash. Requested full snapshots validate publication. Arrays are actual CPU Assets<Mesh>, **not GPU readback**. Native/Web screenshots and live playback inspection are separate acceptance evidence.

Materials explicitly convert diffuse RGBA to sRGB white-tinted StandardMaterial with roughness0.7, metallic0, alpha Mask(0.5); partial alpha is lost at cutoff. Hair disables backface culling and uses double-sided lighting. Eyes cull backs. Fixed OBJ assets contain no vn; source-position-shared fitted area normals are skinned with full inverse transpose blends. No normal map/litsphere/SSS or shader fetch.

Build with build/build.py inside one fresh wefty exec, jobs1/offline/locked; output must be an absolute new path under this worktree's .work/appearance64. The build sequentially compiles Web, exports via existing matching wasm-bindgen, builds native, runs Rust controls, and writes source/artifact receipts. Root owns all launches/GPU/CUA. No worker GUI launch.
