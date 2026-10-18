# Isolated appearance technology preview — contract1

Supports issue79 preparation while issue78 native acceptance is unavailable. This is a separate technical experiment, NOT issue79 production admission. Original motion candidate c655217c0c9c41069b0f45a0d8c2795e455ca6bf, root dependencies, vendor, production source/assets, Work schema and original profiles remain unchanged. Issue79 mainline gate still depends on78. No new downloads/model/API/cloud resources. Root integrates/Git/builds/GPU; workers own disjoint asset and preview source directories.

## Bounded first result

A real live Rust/Bevy Web preview of the SAME B1 character with genuine approved skin texture and correct UVs. Use normal nvwa_studio::build_app() and the same real character/runtime/bones/shape/motion. Add a labeled experimental plain/skin toggle, no static image/model-viewer substitute. Eyes/hair are extracted/authenticated/decoded-inspected in parallel; their actual mesh fitting/rendering belongs to a later slice unless first skin gate is already achieved without scope growth. No claim of AI generation, skin physiology/PBR parity, gaze, hair physics or solved clothes.

## Existing approved inputs

Original approved ZIP (read only; explicit local path passed to packer)280737770bytes SHA256 b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107. Select EXACT10files from docs/research/b1-appearance-readiness.md;10selected payloads6769409bytes. Preserve package item metadata, CC0 full text, MHMAT/MHCLO headers and hashes. No arbitrary archive extraction/path traversal/symlinks/extra dependencies or shader fetches. Extract only to owned experiments62/assets/; inspect PNG decoded data with existing tools/stdlib, no installs. Runtime skin uses only fixed selected RGB2048² diffuse; all extra files are authenticated PREPARATION only, not rendered admission. Packer must record source and output identities and deterministic bound-limited controls.

## Actual rendering rules

- Reuse fitted original source body's actual Mesh UV_0 and duplicate render-vertex order. Prove CPU body vertex order/IDs/indices compatible; do not map UV solely by source ID or flipV twice. Fail on absent/ambiguous binding.
- Only add/bindUV and texture/material; positions/normals/tangents/indices, body/garment counts,53bone frames, source weights, clips, placement and foot/root rules remain unchanged. Get fresh successful unchanged b1_frame_snapshot before/after binding as numeric evidence; original CPU snapshot does not certify material/pixel quality.
- One fixed sRGB diffuse, white base tint, existing plain material/roughness behavior otherwise. No arbitrary MHMAT execution or missing legacy shader parity. Image decoded bounds explicit (skin2048², eyes1024², hair2048²; only PNG RGB/RGBA8 noninterlaced for this experiment, unsupported rejects).
- Preserve original plain material/UV state for toggle restoration; bind to current mesh/material handles and fitted recipe, invalidate on refit/reopen. No global initialized flag or stale prior-green fallback. Error visible; no grey fallback credited as skin success.
- Preview state is temporary and NOT saved into Work. Visible label: experimental appearance, not saved. Do not introduce backend3 or silently upgrade any Work/profile. Native build and Web build/actual rendering reported separately; native GUI remainsNOT-RUN untiluserreturns.
- Expose DOM test controls for plain/skin and read-only report/capture through documented Wasm exports (no injected mutation automation required). Report actual UV/material/image/mesh IDs/counts, decoded image size/format and current parameters/sample identity. Success means actual texture handle/image/UV attached and real image inspected, not merely request submitted.

## Verification scope

First prove one neutral textured render. Then check3torso(-1/0/+1),3jaw(-1/0/+1) and authored arm/knee neutral/peak/end at declared subset; include plain→skin→plain→skin, paused seek, live playback and torso refit while skinactive. Record actual screenshots, material/UV/geometry observations and limitations. Keep independent untextured control, do not hide clothing with camera/texture. No formal performance claim. Independent reviewer inspects source/artifact identity and intended failure/restore checks before adoption decision. A failed result can be kept on an experiment branch; no mainmerge or dependency gate waived.
