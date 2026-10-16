# Raw runtime pose capture v1

One JSON object, `schema_version: 1`, `platform: "native"|"web"`,
`schedule: "PostUpdate.after(AnimationSystems).after(TransformSystems::Propagate)"`,
`status: "complete"|"failed"`, `error: null|string`, `samples: [...]`.
No expected pose values enter the collector. JSON numbers preserve actual f32
values converted exactly to f64. Matrices are 16 numbers in column-major order;
rotations are quaternion `[x,y,z,w]`.

Each sample:
- `source_key_index`, `requested_clip`, `requested_time`, `requested_time_bits`
  (u32); `frame` (collector PostUpdate frame count), `settled_frames`.
- `work`: the complete actual `EditorState.document()` JSON at capture.
- `playback`: actual `clip_id`, `position_seconds`, `position_bits`, `playing`,
  `active_timeline_id`, `seek_pending`, `error`.
- `players`: each `{entity, graph_asset, animations:[{node_index,
  clip_asset, gltf_animation_index, clip_name, seek_time, seek_time_bits,
  paused, weight}]}`. Clip name/index are resolved from actual loaded Gltf
  animation handles and the actual current profile. No graph-position guesses.
- `character_root`: entity ID of actual scene-host ancestor (WorldAssetRoot).
- `nodes`: all Transform-bearing entities in that host's hierarchy, including
  the host, GLB nodes, and mesh primitive children. Each is `{entity, parent,
  name, gltf_node_index, translation:[3], rotation:[4], scale:[3], global:[16]}`.
  `parent` is null for the host. `name` and `gltf_node_index` can be null only
  for host/primitive helper entities. GLB indices are mapped by the current
  loaded GltfNode names, requiring a one-to-one match for every GLB node.
- `skins`: each actual SkinnedMesh component under host is `{entity,
  mesh_asset, gltf_mesh_index, gltf_primitive_index, gltf_skin_index,
  inverse_bind_asset, inverse_bind_matrices:[[16]], joints:[entity IDs]}`.
  Skin ID is resolved by inverse-bind asset identity, mesh identity by actual
  primitive handle. Joint ordering is the actual runtime component order.

The collector fails on missing current Work, readiness errors/timeouts, missing
or ambiguous scene hosts, nodes, transform/parent state, active clip/graph,
nonfinite values, absent skin binding/assets, or clip/time disagreement. It
requests a paused exact seek before runtime transport, then waits two completed
propagation passes with actual player and playback f32 bits matching request.
All seven requested samples must be present for `complete`. Empty/partial raw
captures cannot be interpreted as successful evidence. Startup loads the
unmodified experiment48 Work through the Studio's existing launch `--work` or
Web `?work=` pipeline, with experiment48 asset bytes in an isolated asset root.
