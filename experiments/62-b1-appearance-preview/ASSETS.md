# Authenticated appearance preparation — experiment62

Prepared the fixed10-file subset from the already approved local `makehuman_system_assets_cc0.zip`. No download, install, model run, build or production change. The actual preview should bind only the skin diffuse for its first slice. Eyes/hair are authenticated preparation, with fitting and rendering still NOT-RUN.

## Reproduce

Set `ARCHIVE` to the existing approved local ZIP. The tool has no archive discovery, network access or unpinned input override. A new output directory is required for preparation; `--verify` writes nothing and requires the existing output to match every prepared byte and the exact file set.

```sh
python3 -B experiments/62-b1-appearance-preview/tools/pack_assets.py \
  --archive "$ARCHIVE" --output experiments/62-b1-appearance-preview/assets
python3 -B experiments/62-b1-appearance-preview/tools/pack_assets.py \
  --archive "$ARCHIVE" --output experiments/62-b1-appearance-preview/assets --verify
python3 -B experiments/62-b1-appearance-preview/asset-tests/test_assets.py
python3 -B -O experiments/62-b1-appearance-preview/asset-tests/test_assets.py
```

Actual local prepare and verify completed. Both normal and `-O` test runs passed11 tests. No processes remain. Test temporary files are confined to the owned asset-tests directory and removed.

## Fixed identities

The ZIP was independently rehashed this pass: **280737770bytes**, SHA256 `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107`. All selected member size/hash identities were verified before the first extraction write. No archive entry is extracted using its own path. The tool stages the selected bounded bytes in memory, authenticates every selected member, decodes all three PNGs, verifies the full local CC0 notice and selected metadata, then writes only its fixed output map. The completion manifest is written last.

Skin runtime path: `experiments/62-b1-appearance-preview/assets/skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png`.

| Exact source member / relative asset output | Bytes | SHA256 |
|---|---:|---|
| skins/young_caucasian_female2/young_caucasian_female2.mhmat |1465|8934dd8d8f3beccc1b212c12116a88b3a88d6265e0a5c8fe42eb62e3fb281ab6|
| skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png |3724137|8d1fb3ceedf142fad32a3504eca1feb4539aecca6de66acde1514b9a61fc7ba0|
| eyes/low-poly/low-poly.mhclo |1344|68582e28e9176cba7cfcf35208f671b6201b8d1bc95c32decff61a3160ec34d8|
| eyes/low-poly/low-poly.obj |6604|783fe1e6331162c876520b4c2bed7a8ca06354ca15497e8ebd68bb1b59f4d3de|
| eyes/materials/brown.mhmat |1247|4abad93ce50541c08127721e77bce035640c9f16bed16cd0f5524b1cd5908465|
| eyes/materials/brown_eye.png |610817|4659691c7295ad6206c78b003e5fd0e5f91dcd53032fa914a229bb48cabe424b|
| hair/short04/short04.mhclo |59195|d60640aa4c4ffce1aa269647ba436b6ee0bb21bb948f927b84e27a48d2107157|
| hair/short04/short04.obj |55152|676964a133ee35ffcea1195382bf75542da7a298931e4001bc7b0d7b707225de|
| hair/short04/short04.mhmat |1316|7a3ac74db8478aa0afdb8a596c6fe3997d1a8a09d12211d70e8f1e9f0b7e0e97|
| hair/short04/short04_diffuse.png |2308132|0bef7fc0e403db5a40fabb2111ebfa6f7e8158e204c6e56b8da98e9ef527846e|

These10 payloads total **6769409bytes**, unchanged. Headers, OBJ/MHCLO rows and all source coefficients remain byte exact. No conversion, offset fitting, shader execution, image rewriting or geometry admission occurs here.

The other three outputs are `provenance/selected-items.json`, `licenses/CC0-1.0.txt` and deterministic `asset-manifest.json`. The selected metadata derives only the three item records young_caucasian_female2/brown/short04 from authenticated `packs/makehuman_system_assets.json` (39220bytes, SHA256 `e86f1572432cfd062f372adddba4eb7c2e2e31280e96c29291a970320e0a5df0`). No thumbnails, other textures, OBJ dependencies or arbitrary archive members are copied.

Full CC0 text is byte identical to the admitted repository notice,6962bytes, SHA256 `f6089cba01cb570a24712b41ab8a586ccd3cc5ef53dc266ca50b95c288956d2c`. The three metadata records state CC0/author makehuman_system/MakeHuman Community source. Selected source MHMAT/MHCLO CC0 headers remain intact. These source/package statements support the bounded asset licence inference; PNGs/OBJs do not acquire a separate embedded licence claim, and this does not approve arbitrary addon code or the complete application. See [readiness](../../docs/research/b1-appearance-readiness.md).

## Actual decoded observations

The stdlib decoder checks every chunk CRC and reconstructs every scanline using PNG filters0–4. Only RGB/RGBA8, noninterlaced, compression/filter method0 is accepted. Bounds are4MiB file,2048×2048 pixels,16MiB decoded pixel bytes plus scanline filter bytes,4096 chunks, bounded zlib output with exact end-of-stream. Unsupported transparency chunks/formats, trailing bytes and truncated streams reject. Decoded hashes and observed alpha-bin counts are recorded in `asset-manifest.json`.

| Image | Actual decoded layout | Alpha0 pixels | Alpha255 pixels | Partial alpha pixels | Alpha≥128 pixels |
|---|---|---:|---:|---:|---:|
| Skin |2048×2048 RGB8,12582912bytes|0|4194304|0|4194304|
| Brown eyes |1024×1024 RGBA8,4194304bytes|13238|1035294|44|1035314|
| short04 hair |2048×2048 RGBA8,16777216bytes|1745154|1886780|562370|2201816|

RGB skin has implicit opaque alpha. Eyes and hair have decoded alpha min0/max255. Hair's substantial partial alpha requires the later explicit mask/blend decision and visual checks. These are decoded channel statistics, not a selected alpha policy or quality finding. Total actual source decoded pixel storage is33554432bytes (32MiB); GPU allocations/mips/runtime memory were not measured. The preview's fixed sRGB diffuse intent does not claim original MHMAT/litsphere/PBR/ICC rendering parity.

## Rejection controls and limits

The11 tests exercise production-called authenticate/decode/publish/verify functions: exact allowlist exclusion; wrong archive/member hashes and sizes; missing, duplicate, truncated, traversal and symlink archive entries; path separators/absolute/dot components; real CLI failure before output creation; archive-path symlink rejection; all five PNG row filters against independently known pixels; exact RGBA statistics; bad CRC, truncation, unsupported depth/interlace/filter, mismatched dimensions, bounded decompression/extra or short output/trailing stream; existing destination, output symlink ancestor, attempted path escape; verification rejects extra files, changed bytes and symlinks. The extracted13-file manifest and all source/output identities are also checked. Assertions are unittest/check exceptions and remain active under `-O`.

The packer is for this exact immutable experiment subset. Authentication of the complete approved ZIP precedes ZIP parsing/extraction, and all selected member checks and PNG decoding precede publication. An interrupted filesystem write is not success: rerun `--verify`; it requires every byte and the exact file set. No existing output is overwritten by the preparation CLI.

VERIFIED — exact archive/member/output identities, deterministic prepare→verify, actual RGB/RGBA scanline decoding/alpha statistics,11 adversarial/control tests normal and `-O`.

NOT-RUN — UV/body binding, native/Web pixels, actual skin appearance, eye/hair fitting or rendering, alpha policy/quality, material parity, hair physics, collision, production asset/profile admission or issue78 acceptance.
