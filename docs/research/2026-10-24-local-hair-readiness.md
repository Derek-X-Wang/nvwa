# #79 local replacement hair inventory — 2026-10-24

**NO-GO now for a future one-asset comparison:** the approved system ZIP was not found in the bounded checked scope. short03 remains a historically identified fallback, with current local availability **UNKNOWN**. No extraction, new candidate, render, fitting, model run or download occurred. No replacement is admitted and no visual improvement is claimed. Current short04 remains A.

## Current files verified

All four files under `assets/appearances/mpfb-b1-cc0-v1/hair/short04/` exist and match `SOURCE.json` now; total **2,423,795 B**.

| Existing A file | Bytes | Fresh SHA256 |
| --- | ---: | --- |
| short04.mhclo | 59,195 | `d60640aa4c4ffce1aa269647ba436b6ee0bb21bb948f927b84e27a48d2107157` |
| short04.obj | 55,152 | `676964a133ee35ffcea1195382bf75542da7a298931e4001bc7b0d7b707225de` |
| short04.mhmat | 1,316 | `7a3ac74db8478aa0afdb8a596c6fe3997d1a8a09d12211d70e8f1e9f0b7e0e97` |
| short04_diffuse.png | 2,308,132 | `0bef7fc0e403db5a40fabb2111ebfa6f7e8158e204c6e56b8da98e9ef527846e` |

Fresh metadata: 865 source positions; 991 UV rows; 525 quads / 1,050 fan triangles; 991 distinct position/UV pairs; every source position used. UV V reaches 1.0031, so preserve the existing sampler behavior rather than silently clamping source UVs. These are source counts, not runtime upload or beauty evidence.

Proxy: HM08 UUID `e09bfd91-f83f-4f9a-ba8c-4635cd1ae0d8`; 865 nine-column rows; helper IDs 215–12,366 inside the 19,158 cage. There are 42 negative coefficients in 40 rows (range −0.16327…1.11002). No explicit rig/vertex weights or delete-verts declaration was found. Signed coefficients must remain signed.

PNG: 2048×2048, 8-bit color type 6 (explicit RGBA), noninterlaced. All chunk CRCs checked. This pass did not decode alpha pixels or score coverage. Existing decoded SOURCE.json statistics are historical, not a new alpha audit.

## short03 identity retained from repository evidence

`docs/research/b1-source-replacement-plan.md` records the exact four-file subset below, **2,538,053 B**. These identities were **not freshly authenticated**, because the archive is missing from checked locations.

| Recorded local fallback member | Bytes | Recorded SHA256 |
| --- | ---: | --- |
| hair/short03/short03.mhclo | 69,048 | `d80bbb8fd9b06721c481756fb3e1d6dce04fcfc9ca8a379edd4ea3c0d81ed17f` |
| hair/short03/short03.obj | 74,766 | `4a9fc385718f2c46fb328ab99d33e3a946cecdb717987c8b324cf2466b59bd9c` |
| hair/short03/short03.mhmat | 1,309 | `8dcf42b677301ab6a66f96ff41751ecf88fba6c6cd7c564e6953f9c78e40a8fd` |
| hair/short03/short03_diffuse.png | 2,392,930 | `fe6ed0bb14498a48a2e8fc07e80e2a6f62c8b67686fcd0a7a570d345faec97da` |

Recorded source topology: 1,011 positions, 1,071 UV rows, 961 faces, 1,922 fan triangles; HM08 UUID `a6cb8ad2-2e0d-4655-81ef-bfce1676ec67`. PNG dimensions/alpha, signed mapping rows, helper coverage and material dependencies are **UNKNOWN / NOT-RUN this pass**. Recorded Female/Short tags do not establish intended body fit.

## Exact source availability and license limits

The original delivery receipt identifies unversioned `makehuman_system_assets_cc0.zip`, **280,737,770 B**, SHA256 `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107`; retained Last-Modified is 2024-04-14T13:28:46Z. Neither member timestamps nor that HTTP timestamp is a semantic release. No upstream published digest was recorded.

The exact ZIP filename was absent at:

- `$TASK_CHECKOUT/.work/character-approved-20261016/downloads/makehuman_system_assets_cc0.zip`
- `$PRIMARY_CHECKOUT/.work/character-approved-20261016/downloads/makehuman_system_assets_cc0.zip`
- `$HOME/Downloads/makehuman_system_assets_cc0.zip`
- `$FOUNDATION_CHECKOUT/.work/character-approved-20261016/downloads/makehuman_system_assets_cc0.zip`

The task record identified the last path as the original approved-download checkout. Its direct `experiments/53-character-comparison/downloads/DOWNLOAD-REQUEST.md` and `delivery/system-assets-download.json` were also absent. This was the final narrow lookup; no further discovery followed.

Direct child project work-product roots matching source/replacement/inventory/appearance/hair/character/B1/2026-10-16/2026-10-17 were listed. Their listed direct artifacts did not identify a retained system ZIP. The directly named `2026-10-18-character-quality-round/ARCHIVES.json` retains garment/eyes references, not this ZIP. No recursive filesystem search, archived-worktree recovery or whole-disk scan was attempted. Absence outside this bounded scope is not claimed.

Freshly hashed existing CC0 text: 6,962 B, SHA256 `f6089cba01cb570a24712b41ab8a586ccd3cc5ef53dc266ca50b95c288956d2c`. Existing selected metadata: 1,097 B, SHA256 `e72ef98539743548e7a9e1622c308d6493cfa9d14533c4044e1095913e4a8b71`; short04 is `makehuman_system` / CC0 / MakeHuman Community. Current OBJ/MHCLO/MHMAT headers state September 2020 CC0 with Data Collection AB, Joel Palmius and Jonas Hauquier.

For short03, the plan records equivalent selected-header/pack CC0 evidence; full pack member `packs/makehuman_system_assets.json` is recorded as 39,220 B / SHA256 `e86f1572432cfd062f372adddba4eb7c2e2e31280e96c29291a970320e0a5df0`. That pack member and short03 headers were not reopened now. License evidence does not cover absent legacy shader code or establish material parity.

**New network bytes used: 0. New network bytes needed for this subset NOW: UNKNOWN.** The historical claim of zero required bytes cannot be reconfirmed without the retained source. This report does not authorize retrieval.

## Minimum compatibility risks before any later trial

- Runtime is pinned to short04 paths/count 865/texture size 2048 and authenticated fixed manifests (`appearance/geometry.rs`, `assets.rs`). A short03 drop-in is not currently supported. A later authorized experiment needs a separate explicit identity and count/dimension contract.
- Current importer uses OBJ position/UV corners, fan triangles, full source coverage and V-flip. Raw OBJ positions do not become the fitted mesh; helper mapping does. Preserve topology and prove actual source-to-upload correspondence later.
- Current mapping converts MHCLO offsets and scale references once by 0.1 into the metre cage. Preserve signed helper coefficients, normalized coefficient rows and scale rules. Exact author-intended cage/recipe remains unknown; HM08 alone does not prove fit.
- Current runtime transfers fixed 53-bone helper weights, retains positive final aggregates and normalizes all retained influences without a four-bone cap. No short03 transfer or skinning was run.
- Keep `simple-srgb-mask-v1` behavior: mask 0.5, hair double-sided/no culling, fixed simple material. Recorded short03 MHMAT uses legacy AlphaToCoverage/litsphere metadata, references no normal map, and its shader/`data/litspheres/lit_hair.png` are recorded absent from the ZIP. Do not fetch dependencies or change rendering policy to obtain a pass.

Once an exact already retained ZIP is provided and authenticated, the bounded subset could be inventoried for a separately approved future A(short04)/local-short03 comparison. This is a source-readiness condition only. It gives no reason to expect short03 to look better.

All old alpha/mip/fringe/frontarch failures remain failures. Experiment 86 remains STOP / NO-ADOPT for insufficient visible gain and was not rerun or adjusted. #79 current A, #80 HOLD, 99-point diagnosis backup/full21-before-fit, #112 FAIL, #3 blocked and #4 measurement gaps remain unchanged. Eye and clothing work is unchanged.

**PARTIAL —** current A bytes/topology/proxy/PNG headers and CRCs verified; local short03 source availability and fresh identity remain UNKNOWN. **NOT-RUN —** short03 extraction, alpha decode/score, import/fit/weights/upload, endpoint rendering, visual comparison, acceptance, build/CI/portable tests. No services, tabs, ports or worktrees created. Writes are confined to this `hair/` report directory and are now stopped.

Publication note: checkout/home prefixes above are descriptive placeholders for the exact task-local locations checked. No additional search or measurement was run for publication. Original inventory/receipt remain retained privately.
