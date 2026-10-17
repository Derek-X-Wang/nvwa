# B1 appearance readiness proposal — issue79

Status: **proposal, gated by [#78](https://github.com/Derek-X-Wang/nvwa/issues/78) acceptance**. [#79](https://github.com/Derek-X-Wang/nvwa/issues/79) would add one fixed skin/eyes/short-hair preset to the same fitted B1 body, sportsuit,53-bone rig, two shape parameters and authored motions. This proposal performs no extraction or product admission. This docs-only pass changed no source, asset, lock, build or runtime state.

## Existing local bytes and provenance

Earlier bounded inspection found all10 selected files in the already downloaded official system-assets container, `makehuman_system_assets_cc0.zip`:280,737,770bytes, SHA256 `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107`. The [delivery receipt](../../experiments/53-character-comparison/delivery/system-assets-download.json) records the download. This is an unversioned official snapshot, with retained Last-Modified2024-04-14T13:28:46Z; member timestamps2020-01-01 are not a semantic release version. No upstream published archive digest was available. This pass did not reopen or rehash the archive.

| Selected preset component | Exact ZIP members | Source payload |
| --- | --- | ---: |
| Skin, young_caucasian_female2 | `skins/young_caucasian_female2/young_caucasian_female2.mhmat`; `skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png` | 3,725,602bytes;2048² RGB8 diffuse |
| Low-poly brown eyes | `eyes/low-poly/low-poly.mhclo`; `eyes/low-poly/low-poly.obj`; `eyes/materials/brown.mhmat`; `eyes/materials/brown_eye.png` | 620,012bytes;1024² RGBA8 texture |
| short04 hair | `hair/short04/short04.mhclo`; `hair/short04/short04.obj`; `hair/short04/short04.mhmat`; `hair/short04/short04_diffuse.png` | 2,423,795bytes;2048² RGBA8 diffuse |

Total: **6,769,409bytes**, excluding notices and pack metadata. These remain archive-resident; no new download is needed. The separate existing MPFB2.0.18 container is45,956,992bytes, SHA256 `c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad`, with pinned source commit `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e`. It is not an additional runtime requirement for this preset.

Earlier inspection recorded these per-member SHA256 values; a later extraction gate must check them again before conversion:

```text
8934dd8d8f3beccc1b212c12116a88b3a88d6265e0a5c8fe42eb62e3fb281ab6  young_caucasian_female2.mhmat
8d1fb3ceedf142fad32a3504eca1feb4539aecca6de66acde1514b9a61fc7ba0  young_lightskinned_female_diffuse2.png
68582e28e9176cba7cfcf35208f671b6201b8d1bc95c32decff61a3160ec34d8  low-poly.mhclo
783fe1e6331162c876520b4c2bed7a8ca06354ca15497e8ebd68bb1b59f4d3de  low-poly.obj
4abad93ce50541c08127721e77bce035640c9f16bed16cd0f5524b1cd5908465  brown.mhmat
4659691c7295ad6206c78b003e5fd0e5f91dcd53032fa914a229bb48cabe424b  brown_eye.png
d60640aa4c4ffce1aa269647ba436b6ee0bb21bb948f927b84e27a48d2107157  short04.mhclo
676964a133ee35ffcea1195382bf75542da7a298931e4001bc7b0d7b707225de  short04.obj
7a3ac74db8478aa0afdb8a596c6fe3997d1a8a09d12211d70e8f1e9f0b7e0e97  short04.mhmat
0bef7fc0e403db5a40fabb2111ebfa6f7e8158e204c6e56b8da98e9ef527846e  short04_diffuse.png
```

The ZIP's `packs/makehuman_system_assets.json` was recorded as39,220bytes, SHA256 `e86f1572432cfd062f372adddba4eb7c2e2e31280e96c29291a970320e0a5df0`. Its selected item keys young_caucasian_female2, brown and short04 each state CC0, author makehuman_system and MakeHuman Community source. Selected MHMAT/MHCLO headers also state CC0, September2020, and name Data Collection AB, Joel Palmius and Jonas Hauquier. PNG/OBJ files are the named dependencies of those items; no separate embedded PNG licence claim is made.

Preserve exact headers, item metadata, original/converted hashes and the [full CC0 text](../../assets/characters/mpfb-b1-v1/licenses/CC0-1.0.txt). The existing [source admission report](../evidence/b1-work/SOURCE-ADMISSION.md) separates asset data from program/configuration/shader code and records broader application release limits. CC0 evidence for these selected assets does not clear arbitrary addon code or establish complete application distribution approval. The [earlier garment extraction receipt](../../experiments/53-character-comparison/delivery/system-garment-extraction-receipt.json) remains a distinct, unchanged admission boundary.

## Recommended identity and bounded implementation

Use **a new asset ID, descriptor and canonical appearance profile with explicit `b1_cpu` backend version3**. Names are for root to freeze; none is admitted here. Keep Work schema3. Preserve existing static version1 and motion version2 identities, exact13-file descriptors and two-part behavior described in [ADR0007](../adr/0007-versioned-character-backends.md) and the [motion contract](../implementation/b1-motion-contract.md). Creation must be explicit; no saved Work is silently upgraded.

A new asset/profile under backend2 is technically possible because old readers reject unknown assets. It would broaden version2 into two material/part contracts and still require per-asset branches in all exact validators. Version3 makes the four-part, authenticated-texture contract explicit while reusing the same motion and full-positive CPU skinning. Root must decide this before implementation. Accepting version3 alone is insufficient: current `is_b1_motion()` means exactly version2, so transport/UI capability dispatch must explicitly include the new profile.

A self-contained package retaining13 old inputs plus10 selected files has **23 payload files and12,494,516bytes**, before descriptor/notices or conversion-size changes. This exceeds today's8MiB total cap. Every selected file fits the4MiB per-file cap. Freeze a separate appearance total and decoded-image pixel bounds; do not increase existing version1/2 limits globally. No appearance editor, arbitrary material importer, extra outfit texture, new expression, gaze channel or hair physics is proposed.

## Reusable source seams and remaining risks

| Boundary | Current seam and proposed use | Required limit/check |
| --- | --- | --- |
| UVs | [Humentity fit](../../vendor/humentity/src/assets.rs) preserves UV_0; [B1 upload](../../crates/nvwa-runtime/src/b1.rs) currently rebuilds positions/normals/tangents/indices only. Copy fitted UV_0 once to the CPU display. | Match duplicated render-vertex order and indices. One source ID can have several seam UVs. [OBJ loading](../../vendor/bevy_obj/src/util.rs) already flips V; do not flip twice. Inventory's identical21334 UV/18486 face rows support a relationship, not rendered alignment. |
| Geometry units | Reuse documented×0.1 OBJ-position and MHCLO offset/reference-scale conversion; axes, UVs, indices and signed mapping coefficients stay unchanged. | Pin both source and converted bytes; inspect new proxy source-ID/helper coverage and any delete_verts masks. Preserve garment-only body masking until a new mask's exact meaning is approved. |
| Proxy deformation | Reuse [full_proxy_influences and PreparedSkin](../../crates/nvwa-b1-adapter/src/lib.rs), fitted rest/gauge caches and actual propagated bones. | Hair has42 signed coefficients; preserve existing row normalization and positive **final aggregate** policy, not coefficient clamps or top-four truncation. Inventory reports242/865 hair vertices with >1% non-head weight: do not turn it into a rigid head cap. |
| Eyes | Existing low-poly mesh has96 vertices/96 UV rows/86 faces; all96 helper mappings have head=1 in the source inventory. | Fit/eyelid contact is unverified. Current rig has no eye bones; head-following is the bounded hypothesis, with no independent gaze/eyeball control. |
| Materials | Translate only a fixed reviewed base-color/alpha subset into simple authored materials. Keep sportsuit's plain material. | Legacy litsphere shaders/images are absent. No legacy/PBR/skin/cornea/anisotropic parity claim. Do not follow arbitrary MHMAT paths or fetch missing dependencies. |
| Alpha | Skin is opaque sRGB diffuse. Inspect eye alpha before choosing its policy. For hair, compare an explicit mask policy, proposed cutoff0.5, two-sided cards and declared shadows. | RGBA headers do not prove useful alpha. Native/Web hairline, holes, shadows and sorting need actual rendering. A blend fallback needs a new explicit decision. |
| Transaction/cache | Reuse authenticated immutable bytes, candidate Open and fit-once/skin-per-frame lifetime. Add four exact parts and required image/material/UV bindings. | All meshes/materials/decoded images must succeed before commit; no grey fallback counted as success. A global initialized flag must not reuse another descriptor's verified source. Keep old two-part assertions; add a separate exact four-part contract. |

PNG support already exists in the workspace. Three RGBA8 images at these sizes would allocate36MiB before mipmaps/other copies, approximately48MiB with full mip chains. These are size calculations, not observed memory or performance. Texture/image handle lifetime, decoded-byte bounds and missing/swapped/late texture failures require tests.

## Decision and acceptance gates

After #78, root freezes the asset/profile/backend identity, exact converted package and bounds, material/color-space/alpha settings, mask policy and validation cohort. Then selectively extract/authenticate only the listed local members. First prove body UV/index equality and visible skin alignment; add fitted eyes/hair through the same rig and full-positive weights. Reuse the nine torso/jaw recipes and both authored motions, preserving all joint/foot/garment limits and known fold/poke-through/M2 HOLDs.

Native and Web each need actual fixed-camera neutral/peak/end and motion comparisons at face/eyelids/hairline/neck/shoulders. Keep an untextured geometry control so appearance cannot hide existing defects. Save/Open/CLI exchange must retain the explicit new identity. Verify four-part binding, texture failures, recovery and bounded resources. Record geometry correctness, render parity, measured resource behavior and human appearance judgment separately. The prototype can be rejected without broadening character admission.

**PARTIAL —** current source seams, exact identity/part-count constraints and payload arithmetic inspected; archive/member/licence facts above come from the earlier bounded local inventory. **NOT-RUN —** extraction, conversion, appearance admission, actual alpha inspection, eye/hair fitting and deformed rendering, native/Web appearance, memory/performance measurement and visual-quality approval. Root's unresolved choices are identity versioning and the exact material/alpha/mask contract, after #78 acceptance.
