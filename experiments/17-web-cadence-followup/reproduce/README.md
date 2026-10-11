# Post-run reproduction and evidence verification

These are published reproduction copies. Their bytes were **not** the measured bytes. `source-manifest.json` records each original measured SHA256, each published SHA256, and the transformation. The path-redacted diff shows the changes. Root preserves the exact originals privately.

Only path/layout handling, explanatory copy notices and optional helper-result output changed. Helper assertions remain unchanged. The all-pair 10% rule, unknown-focus DEFER rule, finite mixed-window limit, exclusive output creation and owned server cleanup remain unchanged. The exact root collector is published separately in `../evidence/public/root-collector.js`; its final hash is recorded, with no pre/post seal claim.

From the repository root, verify committed evidence without creating any renderer, server or compiler process:

```sh
python3 -B experiments/17-web-cadence-followup/reproduce/verify-publication.py
```

Run the lightweight helper regression checks, which use only bounded task-owned sleeper processes:

```sh
python3 -B experiments/17-web-cadence-followup/reproduce/check-followup.py
```

Helper checks print to stdout by default, so the invocation remains repeatable on the published layout. Pass `--output /approved/new/file.json` to retain a new result; exclusive creation refuses overwrites. Retained post-run check output under `reproduce/evidence/` is distinct from measured-source preflight evidence under `evidence/public/`.

Future measurements require the exact preserved A/B bundles and a fresh exclusive root GPU lease. There is no build command here. The portable script derives the primary checkout from Git's common directory. `NVWA_PRIMARY_CHECKOUT` can explicitly select a root-approved checkout containing the preserved bundles. A missing or different bundle fails identity verification; rebuilding cannot recreate a byte-identical accepted artifact.

Use `python3 -B .../reproduce/followup.py --help` for actions. A fresh future collection writes its pre/post identities and seals under `reproduce/evidence/` and raw captures under ignored `.work/perf27/raw`. Existing measured outputs must be retained and must not be replaced. Use the path-redacted `COLLECTION.md` as a plan and replace its placeholders with approved local paths. Root's collector requires advertised CUA bindings and capabilities; do not substitute CDP or OS input.

`PUBLICATION_FILES.json` in the parent directory is the exact proposed commit inventory. It excludes original measured local-path sources, complete private process snapshots, failed audit candidates and the authoritative ignored raw data. Root performs the final privacy review, preserves ignored raw/originals, and publishes.
