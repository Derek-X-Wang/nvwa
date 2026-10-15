# Independent source authority and fixture geometry capsule

This capsule adapts the independently frozen first-source audit. It supplies factual reference inputs for experiment 47. It neither tests the primary calibration math nor admits playback, export, or a generated action. The first audit read original cached upstream text before any experiment 46/47 candidate inspection. That reading order is a process assertion, not a cryptographic property of a checksum.

The original freeze manifest is retained byte-for-byte as [original-first-freeze.json](original-first-freeze.json): SHA-256 `9e9c880f214b0d77ea27fc893df2b3b577263212f7e5b5d8b5c93722a34b5043`. The private first report hash is `9ddd992efb4af47cd524ec55124a28889448208541f4a73ab08f7a74462a19d2`; original derivation script hash is `2f057bdf5aa370bd2fc3253ce5644b3bb81613fb847ac2a510badbab42bdb3ef`. Their full manifest records five immutable first-pass artifacts. [adaptation-record.json](adaptation-record.json) describes each public transformation without private home paths. [input-hashes.json](input-hashes.json) identifies all 21 original inputs; eight byte/URL receipt matches remain in [original-receipt-matches.json](original-receipt-matches.json).

## What the evidence establishes

The actual fixture eye geometry establishes front +Z and up +Y after the proper Blender-to-GLB map `(x,y,z) → (x,z,−y)`. Pupil centers are at Z=.172, beyond white centers at Z=.148, and eye height is Y=1.672. The frozen authoring source independently places nose, pupils, painted mouth, and brows toward Blender −Y. Camera placement is not used.

Body left is `up × front = +X`. Source SOMA30 LeftArm/LeftHand/LeftLeg/LeftEye are at +X. Exact target bind origins place `.L` at negative X and `.R` at positive X. Thus target suffix identity conflicts with bodily side. Author intent for the suffixes is unknown. Preserving target suffixes, front, and up together requires reflection; a rotation cannot achieve all three. The root-selected implementation policy preserves physical front/up and corresponds source Left to target `.R`, with names unchanged. That policy is not calibration admission.

Source thumb and middle endpoints form a non-collinear hand plane: cross magnitudes are .0108698018 and .0108092061 square meters. Source and target geometry therefore provide more information than terminal joint origins alone. However, no inspected original source identifies an exact signed palm/volar normal or sole/contact surface. Target hand thickness and thumb asymmetry, authored bone roll, and foot forward/down geometry support explicit engineering gauges. Such gauges must retain their authorship and limits. They do not certify anatomy.

Source local rotations are parent-relative orientations. Source identity rest is the C++ exporter T-pose layout; target bind rotations contain authored roll and an A-like arm pose. Their neutral correspondence and twist-zero mapping are engineering conventions. The first animated frame is not a neutral authority. Source static decoder cross-product algebra forms proper rotations for valid inputs; actual runtime decoder parity remains NOT-RUN.

## Claim, primary source, exact identity, and line reference

This table paraphrases inspected sources; no third-party source code or document body is redistributed. Exact URLs and hashes also remain machine-readable in [authority-claims.json](authority-claims.json). Archived source identities are bound to the existing [experiment 41 receipts](../../41-real-short-motion/evidence/source-receipts.json) and [source index](../../41-real-short-motion/evidence/source-index.json).

| Claim | Immutable original source | SHA-256 | Original lines |
|---|---|---|---|
| SOMA30 names and parent-local offsets; original extraction provenance remains a provider claim | [cpp-src__skeleton.hpp](https://raw.githubusercontent.com/localai-org/kimodo.cpp/5679ff19ba0a522c0b0516e9a9d402fe1af2c027/src/skeleton.hpp) | `6c1e1d98170a99105bd325c32caff5421bfb20d1e16160980a9f2c3258e244a3` | 10, 12, 45, 67, 91 |
| Parent-relative orientation is transpose(parent global) times child global; quaternions XYZW; valid six-vector rotation construction is proper by static algebra | [cpp-src__motion_decode.cpp](https://raw.githubusercontent.com/localai-org/kimodo.cpp/5679ff19ba0a522c0b0516e9a9d402fe1af2c027/src/motion_decode.cpp) | `d9f0076d3254cd6d89719a0097c09aa265fea8ad3404bf303d527b90ce5714ff` | 7, 12 |
| Provider exporter uses identity local rest orientations and translation-only inverse binds; root placement differs from the zero-root source skeleton | [cpp-scripts__export_glb.py](https://raw.githubusercontent.com/localai-org/kimodo.cpp/5679ff19ba0a522c0b0516e9a9d402fe1af2c027/scripts/export_glb.py) | `574a5f1f20476268e33b0007aa2ec212eb5f28767895d810130cc7a639b0cabb` | 20, 35, 40, 49, 108, 117, 197, 206 |
| Official SOMA output uses standard internal zero T-pose; BVH default can use a different dataset rest convention | [official-output-formats.md](https://raw.githubusercontent.com/nv-tlabs/kimodo/58e781898b3d7e328a676a75d3e338c45dce3ad9/docs/source/user_guide/output_formats.md) | `f3f9dcdc1fa21846469791d59977f5d06213225aea63960f9001654379ea163d` | 28, 38 |
| Official description distinguishes internally predicted SOMA30 from public SOMA77 visualization/exports | [official-skeleton.md](https://raw.githubusercontent.com/nv-tlabs/kimodo/58e781898b3d7e328a676a75d3e338c45dce3ad9/docs/source/key_concepts/skeleton.md) | `88c94293365af8ed2017d8c238a65b7d4efeac189cb78c128ad50ca04ddf7987` | 12, 27 |
| Official Kimodo axes are Y up and Z forward | [official-output-formats.md](https://raw.githubusercontent.com/nv-tlabs/kimodo/58e781898b3d7e328a676a75d3e338c45dce3ad9/docs/source/user_guide/output_formats.md) | `f3f9dcdc1fa21846469791d59977f5d06213225aea63960f9001654379ea163d` | 72, 73 |
| Source hand thumb and middle endpoints form a non-collinear plane; no inspected document certifies a volar normal | [cpp-src__skeleton.hpp](https://raw.githubusercontent.com/localai-org/kimodo.cpp/5679ff19ba0a522c0b0516e9a9d402fe1af2c027/src/skeleton.hpp) | `6c1e1d98170a99105bd325c32caff5421bfb20d1e16160980a9f2c3258e244a3` | 47, 50, 59, 63 |

The source constants' comment attributes offsets to original trusted-container bind assets. Those original asset bytes and original `definitions.py` were not inspected. That attribution remains a provider claim. The NVIDIA skeleton and output-format documents themselves were present in the original cache and matched their receipts.

| Target reference | Frozen repository source | Line / binary location | Independent condition |
|---|---|---|---|
| Face/front | `tools/blender/generate_fixture.py`, SHA-256 `bc54eec314ccba2ca2a77499b03d96b1ec9afb8c38cfbb9ac9e1fb04f5736f0e` | 64–66, 101–105, 199–209 | Nose/paint/pupils face Blender −Y. |
| Proper coordinate conversion | Same generator; `assets/fixtures/nvwa-humanoid.glb`, SHA-256 `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6` | Generator 301–305; GLB nodes18–21/meshes0–3 POSITION accessors | All four actual eye centers equal authored `(x,z,−y)` within 1e−6; map determinant +1. |
| Suffix conflict | Same generator and GLB | Generator 156–162; target skin0 hierarchy | `.L` hand X≈−.570000109, foot X≈−.154999963; bodily left is +X. |
| Bind roll | Same generator and GLB | Generator 141–149; skin0 inverseBindMatrices and node TRS | All 18 bind transforms compose with inverse binds within 1e−6; roll fixes authored frames, not palm/sole anatomy. |
| Hand/foot reference limits | Same generator | 69–75, 98–100, 156–162 | Hand thickness/thumb and foot forward/down are authored; no palm tag, flat sole plane, or contact patch is supplied. |

## Portable verification

Run from the repository root with Python 3. The audit resolves its inputs from its own file location and also works when invoked by absolute path from another directory:

```sh
python3 experiments/47-fixture-rig-calibration/reference/audit.py
python3 -O experiments/47-fixture-rig-calibration/reference/audit.py
python3 experiments/47-fixture-rig-calibration/reference/test_audit.py
```

`audit.py` uses only the standard library and explicit exceptions. It parses the actual frozen fixture, checks eye POSITION accessor values, independent conversion parity, bind hierarchy and inverse binds, source metadata/frame facts, retained claim identity, eight archived receipt bindings, and exact geometry/metadata/generator pins. It does not import or execute primary experiment 47 calibration code. Mutation controls invoke this same public CLI in normal and optimized modes and require specific rejection of wrong side, reversed front, changed eye geometry, changed source pin, and false palm certification, plus changed retained source-claim text. Changed-eye rejection occurs at the geometry check before the final file checksum.

**CI without the original cache verifies geometry, metadata pins, and retained claim identity. It does not freshly inspect original upstream text.** The official up/front claim remains bound to the exact experiment 41 receipt identity and original lines 72–73. Receipt hashes establish retained bytes/claims, not truth of undocumented anatomy. No network access is needed or performed.

VERIFIED — Normal and optimized public audit paths pass; six mutations each reject at their intended boundary in both modes, with restored-green checks. Results are retained in [audit-results.json](audit-results.json) and [mutation-results.json](mutation-results.json). The original 21-input/eight-match identities remain intact; current IBM residual is 4.73e−7.

NOT-RUN — Fresh CI original-source-text inspection, original official SOMA bind/surface verification, runtime decoder parity, anatomical palm/sole/contact calibration, primary retargeting math review, model/Blender execution, generated playback, export, and product admission. This helper is authority input implementation, not independent R2 review.

Cleanup: controls remove temporary mutated inputs and use bounded synchronous subprocesses. No persistent worker, server, model process, or acquired resource is created. Root owns retention of this capsule and the private first-pass evidence.
