# #79: one authenticated short03 asset A/B

Temporary experiment only. A is exact original short04. B uses independently authenticated MakeHuman system asset short03, UUID `a6cb8ad2-2e0d-4655-81ef-bfce1676ec67`, basemesh `hm08`, with the original MHCLO, OBJ and diffuse PNG. `SOURCE.json` pins all four asset files and the pack metadata. B has 1,011 source vertices, 1,071 unique position/UV render corners and 1,922 triangles from 961 quads. All source files remain byte-exact; there is no 86 front-arch deformation or alpha edit.

The existing 86 controller, request protocol, full numeric mirror and apply/restore path are reused. The only live changes are the B enum, authenticated B import/PNG decode and B source-map selection. Both use the same actual body cage, signed MHCLO coefficients, decimetre references/offsets converted by 0.1 once, all final-positive weights over all 53 bones, normal recomputation and CPU skinning. Original A replay must match production buffers exactly before B publication. The same entity/image/material handles, image policy, material policy, placement and all other surfaces remain fixed. Mesh/image/bounds restoration remains the old called mechanism.

`cpu_replay.py` is a byte-exact copy of the retained 78 scalar mirror. `source_check.py` supplies short03 through its existing source function. `validate.py` is a source-specific derivative of the strict 86 record checker. It binds each variant's source map, rest fit, normals, full weights, upload and diffuse hash to the authenticated source and actual captured cage/bones. It preserves whole-envelope A/B invariants except the named B asset fields and exact A1/A2 restoration. It does not weaken the old validator or admit rendered quality.

Offline controls:

```sh
python3 -B -m unittest discover -s experiments/89-hair-short03-ab -p 'test_*.py'
```

Rust `candidate::source_tests` executes the actual publication-called B import and image decode, unchanged geometry functions, exact A replay, malformed input controls and a five-positive influence case whose fifth bone contributes to skinning. It requires root's compile release and the authenticated default capture via `NVWA89_FIXED_CAPTURE`. The existing allowlist and other compile-referenced Works stay byte-exact; their presence is not cohort execution. Head-width-plus fitting is NOT-RUN because no fixed actual cage fixture was available in the bounded input search.

The Python tests use a historical exact A capture and construct synthetic B records for control testing. They are not new Web/runtime or image evidence. After offline PASS, independent review and root freeze, root owns one fresh-page default-Work source0 Combined/Textured A -> B -> A comparison, with fixed camera, stage and viewport. An obvious improvement without regression is required before existing bounded full acceptance. Otherwise STOP/HOLD, with no tuning or expanded capture framework. No native UI, CLI/Work-save, GPU contact or adoption claim follows from these tests.
