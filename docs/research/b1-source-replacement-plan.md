# Character source replacement plan — draft, no replacement admitted

The next bounded comparison should test the existing **high-poly eyes** first, keeping the current low-poly eyes as A. **short03 hair** is a local fallback for a separate later comparison. No corrected sportsuit or garment authoring recipe was found in the two retained archives, so no garment replacement is selected.

This plan concerns eyes, hair and one garment. It is an inventory and comparison plan, not a replacement implementation, a visual repair result or product admission. The eight-parameter character implementation remains a separate candidate with final acceptance pending. Existing appearance, clothing and generated-motion quality HOLDs remain.

## What the bounded evidence establishes

| Experiment | Actual result | Limit that remains |
| --- | --- | --- |
| 67: eye surface probes | Eight retained CPU captures and96 fixed rays yielded13 body-first source triangles in12 quads. Source correspondence and single application of captured display placement were checked. | Sparse ray ordering does not identify anatomical eyelids, erroneous occlusion, GPU pixel ownership or a repair. Some selected eye points are self-hidden. |
| 68: isolated eye views | Native and Web each retain nine paused controls: combined/body-only/eyes-only × textured/unlit-textured/role-tint. The existing low-poly eye silhouette remains visibly faceted with lighting disabled. | Role isolation is diagnostic. The records do not uniquely establish eyelid anatomy, intended fit, GPU fragment/depth ownership or the complete visual cause. |
| 69: one hair mip candidate | The selected coverage-preserving mip candidate was rejected before compilation: mip1 error0.001132965087890625 exceeded its predeclared0.001 bound. | This rejects that candidate, not every mip strategy. It is not a GPU trial or a finding that replacement hair is already better. |
| 70: one sportsuit shoulder defect | At torso+1/jaw0, source triangle200 `[246,244,182]` has historical arm-source2 area/fitted-rest ratio22.0056357384. Thirty retained CPU keyframes reproduce source fit/full-positive LBS/upload within the original limits; maximum reconstructed component error is about1.829e-7m. | Faithful replay does not recover the author's intended body recipe/helper cage or establish a unique cause of the complete visible defect. |

The rejected68 shoulder comparison used the wrong short-torso camera reference for a long-torso Work. A later checker finding concerned normalization of raw positive aggregate weights. Those failures must remain failures; fresh shoulder acceptance needs the corrected tool and separately authenticated long reference. They are not replacement evidence.

## Existing local source identity

The retained inventory checked whole-archive hashes, selected member sizes/hashes and selected ZIP CRCs. It did not extract these candidates to disk, perform a full all-member CRC pass, or render them. This draft reads that inventory; it performs no new archive extraction or download.

| Existing archive | Version identity | Local bytes | SHA256 |
| --- | --- | ---: | --- |
| `makehuman_system_assets_cc0.zip` | Unversioned official snapshot; retained HTTP Last-Modified2024-04-14T13:28:46Z | 280,737,770 | `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107` |
| `add-on-mpfb-v2.0.18.zip` | MPFB2.0.18; commit `d0a32e57a7f915cb2f2b95410e2117648c7bbb7e` | 45,956,992 | `c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad` |

The system archive's member timestamps are not release versions. No upstream published archive digest was available in the retained source record. The retained whole-file SHA256 identifies the exact bytes used here. **New network bytes required for the listed local candidates:0.** Local extraction, authentication and computation would still be separate future work.

The selected system-asset OBJ/MHCLO/MHMAT headers explicitly state CC0 and name Data Collection AB, Joel Palmius and Jonas Hauquier, September2020. Pack item metadata identifies `makehuman_system`, CC0 and MakeHuman Community. This graphical-asset evidence does not license arbitrary addon program code or absent shader dependencies. The selected pack metadata member `packs/makehuman_system_assets.json` is39,220B, SHA256 `e86f1572432cfd062f372adddba4eb7c2e2e31280e96c29291a970320e0a5df0`. Retained CC0 legal text is6,962B, SHA256 `f6089cba01cb570a24712b41ab8a586ccd3cc5ef53dc266ca50b95c288956d2c`.

## First future comparison: high-poly eyes

The exact proposed subset is the high-poly proxy/OBJ plus the existing brown material/texture dependencies. The proxy/OBJ pair is173,372B; the complete four-file subset is785,436B. All bytes already exist locally. The new geometry is an archive-resident candidate, not an extracted or admitted runtime asset.

| Archive member | Bytes | SHA256 |
| --- | ---: | --- |
| `eyes/high-poly/high-poly.mhclo` | 72,490 | `b183cfe37120ab726f9b3f2ea6cd3a64c44ce7b4bd91a77c841cf70c04f83a0d` |
| `eyes/high-poly/high-poly.obj` | 100,882 | `da2493215b708a344c33dc72f2a9a5b8fa985dcc5a70ad3b208995cf871da8e1` |
| `eyes/materials/brown.mhmat` | 1,247 | `4abad93ce50541c08127721e77bce035640c9f16bed16cd0f5524b1cd5908465` |
| `eyes/materials/brown_eye.png` | 610,817 | `4659691c7295ad6206c78b003e5fd0e5f91dcd53032fa914a229bb48cabe424b` |

The raw high-poly OBJ has1,064 positions,808 UV rows,1,020 faces and2,040 fan triangles, compared with the current low-poly source's96 positions and172 fan triangles. These are source counts, not uploaded render counts or evidence of anatomical correctness. The proxy declares HM08 and UUID `2c12f43b-1303-432c-b7ce-d78346baf2e6`, with signed helper rows and scale-reference pairs. Neither those declarations nor the generic MPFB base identifies its exact author-intended body recipe/helper cage.

For a controlled trial:

1. Authenticate only the exact subset above. Preserve original bytes, signed mappings, source units, UV topology and source provenance. Establish the single required unit conversion and full-positive weight transfer before comparing actual uploaded arrays. Do not cap influences, offset the eyes, synthesize a lid or delete body geometry to obtain a pass.
2. Keep the current low-poly source as A. Declare the test Works and limits before sampling. Reuse authenticated current short/long, front/quarter held cases and matching production camera/light/alpha/culling settings. Where the eight-parameter profile is included, retain its separate frozen parameter-cohort obligations and failed cases; do not treat the original two-parameter captures as eight-parameter acceptance.
3. Observe actual fitted/skinned arrays and current entity/material/image bindings on native and Web, then collect separate rendered comparisons and continuous-motion evidence. Combined, body-only and eyes-only views may diagnose contributions, but isolated views cannot substitute for the normal combined character result.
4. Keep the existing `simple-srgb-mask-v1` material policy fixed for this comparison. The selected brown material references absent legacy `data/shaders/glsl/litsphere` and `data/litspheres/skinmat_eye.png`; this subset does not establish MakeHuman reference-material parity. State that limit instead of fetching or silently replacing dependencies.
5. Report visible silhouette, fit and cross-endpoint differences separately. Higher polygon count alone is not improvement or admission. Without an authenticated anatomical/authoring reference, intended eyelid fit remains UNKNOWN even if the alternate eye silhouette looks smoother. Any later product candidate needs a new explicit asset identity and its own review and acceptance evidence.

No high-poly fit, rig, upload, native/Web render, image score or performance trial has run in this inventory step.

## Later fallback only: short03 hair

The archive contains this complete2,538,053B subset. It is the smallest complete OBJ/MHCLO/MHMAT/diffuse subset among the other short01/02/03 styles by member size. That is a bounded inventory choice, not an alpha or appearance score.

| Archive member | Bytes | SHA256 |
| --- | ---: | --- |
| `hair/short03/short03.mhclo` | 69,048 | `d80bbb8fd9b06721c481756fb3e1d6dce04fcfc9ca8a379edd4ea3c0d81ed17f` |
| `hair/short03/short03.obj` | 74,766 | `4a9fc385718f2c46fb328ab99d33e3a946cecdb717987c8b324cf2466b59bd9c` |
| `hair/short03/short03.mhmat` | 1,309 | `8dcf42b677301ab6a66f96ff41751ecf88fba6c6cd7c564e6953f9c78e40a8fd` |
| `hair/short03/short03_diffuse.png` | 2,392,930 | `fe6ed0bb14498a48a2e8fc07e80e2a6f62c8b67686fcd0a7a570d345faec97da` |

Raw source counts are1,011 positions,1,071 UV rows,961 faces and1,922 fan triangles. The proxy declares HM08 and UUID `a6cb8ad2-2e0d-4655-81ef-bfce1676ec67`. `Female`/`Short` tags and scale-reference distances do not identify the exact authoring recipe or prove suitability for this character.

Before any rendered comparison, independently audit source alpha/coverage, signed helper fit, unit conversion, all positive influences and actual source-to-upload correspondence. Retain the current short04 as A. Preserve current hairline failures and compare matched held and motion cases on both endpoints. No normal-map member is referenced by this selected material. Its legacy AlphaToCoverage and shader metadata do not select a new production rendering policy. The referenced litsphere shader and `data/litspheres/lit_hair.png` are absent from the retained system ZIP.

The rejected69 candidate stays rejected. short03's source alpha decode/score, fit, rig, upload and actual endpoint rendering are all NOT-RUN. New network bytes for this local subset are0; no replacement hair is admitted.

## One garment: source gap, no replacement selected

The only sportsuit-named directory found in the retained system ZIP is `clothes/female_sportsuit01/`. It contains the existing raw source and optional material maps below, totaling3,607,692B excluding the thumbnail. These are **raw archive source identities**, not hashes of the converted production metre-space OBJ/MHCLO. Listing the maps does not claim that they are currently bound by production or should be promoted.

| Archive member | Bytes | SHA256 |
| --- | ---: | --- |
| `clothes/female_sportsuit01/female_sportsuit01.mhclo` | 124,049 | `6df057d3116db93afbbbb6d692f92cce84aa16db699f47dd14e825d07c6fd42f` |
| `clothes/female_sportsuit01/female_sportsuit01.obj` | 142,064 | `fd529bb8dd6a994c1e9a3fb2fd8b236f52c0cc7cebb1f6fd9328953d9df6d6ff` |
| `clothes/female_sportsuit01/female_sportsuit01.mhmat` | 1,400 | `1153d5ad8a074f0f02c7102375d6d3ae0b82302b6f3909b5b64609a2d5cfdd6b` |
| `clothes/female_sportsuit01/female_sportsuit01_diffuse.png` | 1,396,429 | `00910e3e85b3dcf48d1aa827b4c075cdc77689989423ff4f75bc67f2e86cc588` |
| `clothes/female_sportsuit01/female_sportsuit01_ao.png` | 1,692,805 | `6faffbb99e3d20faeaf87cdddece43fee7d6b7262de3e55817545809f0368524` |
| `clothes/female_sportsuit01/female_sportsuit01_normal.png` | 250,945 | `2bc78509fc4e74b2346dbb54f7f627644125a41573ee458d624246e337f1d28f` |

No second or corrected sportsuit was found in these archives. The system ZIP contains no `.mhm`, `.mhm.gz` or `.blend` authoring recipe/scene; its only JSON is pack metadata. The MPFB archive contains no MHM/Blender scene/MHCLO proxy and one generic `data/3dobjs/base.obj`. That generic base and its shape targets do not identify the sportsuit author's intended recipe. This is a bounded local search result, not a claim that no corrected asset exists elsewhere.

Keep the current sportsuit replay as A. Before proposing a source correction or replacement, obtain authenticated evidence for the intended body recipe/helper cage, source geometry, signed mapping, intended weights and redistributable source/license. Preserve the neutral/rest and motion-added distinction. Local signed projections are descriptive; they are not a global inside/outside test or collision penetration depth. No heuristic weight retuning, four-weight workaround, body deletion, pose removal, relaxed threshold or material/camera concealment is selected.

The garment replacement identity is **UNKNOWN**. No author-intended recipe or corrected local garment has been identified, and no garment replacement quality claim is supported.

## Delivery and admission boundaries

All three paths retain current assets as A and preserve existing failure records and thresholds. Any proposed replacement remains separate from the eight-parameter product candidate. Source availability, CC0 provenance, source topology, CPU correspondence, actual screenshots, GPU readback, performance and normal UI/Save/Open exchange are distinct evidence categories; none substitutes for another.

#79/#80 appearance and garment quality remain HOLD; M2 generated-motion quality remains HOLD. #3 remains blocked, and #4 retains first-present/cold/GPU-memory measurement gaps. No complete replacement, final eight-parameter admission or main/CI success is claimed by this draft.

VERIFIED — retained inventory reports exact local archive/member identities, selected CRC/license metadata and bounded source searches; prior67/68/69/70 results support only the limits described above. NOT-RUN — candidate extraction, authoring-cage authentication, replacement alpha/fit/rig/upload/render, performance, replacement admission and any new network retrieval.
