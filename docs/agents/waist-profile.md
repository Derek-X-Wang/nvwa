# Static waist circumference profile

`new-character-waist <asset-root> <work.json>` explicitly creates
`nvwa-mpfb-b1-waist-v1`, backend schema 7, immutable asset set v5.
The original ten v4 parameters remain unchanged; `waist_circumference` is a
normalized authored shape displacement in [-1, 1], default 0. It is **not** a
centimeter measurement, pure horizontal waist width, or an anatomical isolation
promise. Torso depth, adjacent surfaces and the fitted sportsuit may change.

The two MPFB 2.0.18 CC0 targets match the historical extraction inventory.
The prior 29 runtime payloads are byte-identical; the two new targets retain
exact decompressed source bytes and the existing loader's single unit conversion.
See `assets/characters/mpfb-b1-v5/provenance/waist-circumference-source.json`.

Old profiles, saved Works and default `new-character` remain unchanged.
There is no automatic upgrade. Studio offers an explicit new-static-waist entry,
with the same parameter preview, commit, undo/redo and save/load commands.

This profile deliberately has an empty clip catalogue and no admitted appearance
set. Animation, skin, hair and eyes are not inherited from v4. Existing static
diagnostic poses and the body plus sportsuit CPU silhouette export are supported.
This does not release prior rig, clothing or motion quality HOLDs.

```sh
nvwa-cli new-character-waist /absolute/assets /absolute/waist.json
nvwa-cli describe-capabilities /absolute/waist.json
nvwa-cli render /absolute/waist.json --assets /absolute/assets --output /absolute/new-capture --mode silhouette
```

Use `set_parameters` to choose coarse visual tiers. Select front and side cameras
with `set_stage`, keeping scale and camera distance fixed for comparison. Inspect
both silhouette images before accepting a tier. Mixed torso/hip extremes require
separate quality checks; successful render alone is not a clothing/contact pass.

Targeted checks:

```sh
cargo test --offline --locked -p nvwa-core --test waist
cargo test --offline --locked -p nvwa-cli --test waist
cargo test --offline --locked -p nvwa-cli --features cpu-render --test cpu_render
cargo test --offline --locked -p nvwa-studio explicit_static_waist
```

Compilation, CPU export, UI harness and actual Web/native UI are separate evidence
levels. No new CI budget or reduced source/negative gate is authorized here.
