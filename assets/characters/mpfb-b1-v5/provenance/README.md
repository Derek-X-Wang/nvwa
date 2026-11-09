# Waist circumference source extension (v5)

`waist-circumference-source.json` describes the two newly admitted CC0 source targets and the unchanged v4 payloads. `waist-source-validation.json` records source/payload checks only, not rendering or quality acceptance.

`parameter-source-receipt.json`, `cheek-volume-derivation.json`, `chin-bones-source.json` and older `legacy-*` records are retained historical provenance for prior extensions; their counts and hashes refer to those earlier snapshots, not the v5 set. The complete current runtime inventory is `runtime-payloads.json`, mirrored in `../manifest.json`. `legacy-v4-*` preserves the immediate predecessor.

The two new source gzip files are retained under `source/torso/`; runtime target files are their exact decompressed bytes. No coordinate or amplitude conversion was performed. The existing runtime loader converts source units by 0.1 once. The parameter is authored shape displacement, not a centimeter measurement or pure horizontal width control. Adjacent torso depth may change.

All prior quality HOLDs remain. Static rendered contours, clothing behavior and motion require separate evidence. No addon program code or new macro data was imported.
