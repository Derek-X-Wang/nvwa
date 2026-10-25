# #79: one authenticated short01 asset A/B

Temporary experiment only. A is exact production short04. B uses the independent MakeHuman system asset short01, UUID `766436e9-63ed-4f6a-afa9-99f3acff70a8`, basemesh `hm08`. `SOURCE.json` pins the original four asset files and pack metadata. B has 2,984 source vertices, 3,177 unique position/UV render corners and 3,678 triangles from 1,839 quads. All source files retain their original bytes and headers. The existing CC0 text is retained unchanged.

This is a minimal clone of experiment89 for one new B asset. Its controller, protocol, apply/restore mechanism, material/image policy and fixed Works remain exact except for B labels and source-map selection. `geometry.rs` and `cpu_replay.py` are byte-exact copies of89. Both variants use the same actual body cage, signed MHCLO coefficients, decimetre references/offsets converted by0.1 once, all final-positive weights over all53 bones, recomputed normals and CPU skinning. Exact production A replay is required before B publication. Entity/image/material handles, placement, camera, stage and other surfaces remain fixed.

The local ZIP was authenticated against the approved 280,737,770-byte SHA256 `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107`. Only the four short01 asset files and complete pack metadata are retained here. No source geometry, alpha, texture, weights or material were tuned. Existing source-specific validator checks and typed-f32 UV equality remain unchanged.

Offline controls:

```sh
python3 -B -m unittest discover -s experiments/91-hair-short01-ab -p 'test_*.py'
python3 -B -O -m unittest discover -s experiments/91-hair-short01-ab -p 'test_*.py'
```

The Python tests authenticate the same historical full-cage default capture used by89 and construct synthetic B records for validator controls. They are not actual Web/runtime/image evidence. The five `candidate::source_tests` call the actual B import/PNG decoder and unchanged geometry path, verify complete fit/weights/normals and exact A replay, and retain malformed/tamper and fifth-positive contribution controls. They require `NVWA91_FIXED_CAPTURE` set to that exact pinned capture. Cargo tests and native/Wasm compilation require root's separate code-review release.

Root owns the one actual default-Work held-source0 Combined/Textured A -> B -> A comparison, with the same fixed camera/stage/viewport. Forehead and both eyes must remain visible; the boundary must show meaningful improvement without an obvious new fit problem. Otherwise STOP/HOLD without tuning or expanding the capture scope. Existing extra Works are retained because the unchanged controller references them; their presence does not prove cohort execution. Native UI, CLI/Work-save, full acceptance, GPU contact, visual gain and adoption remain NOT-RUN at source freeze.
