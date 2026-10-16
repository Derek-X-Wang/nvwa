# Path B — actual Humentity evaluation

2026-10-16. **The real native library and CLI compile, load the approved sample, and execute all eight cases. The unchanged candidate fails the fixed numerical tolerance.** **The separate, authorized one-line B1 ablation passes all eight numerical cases.** No production adoption or graphical acceptance follows from this experiment.

The shared sample is `common-sample.json`, SHA-256 `2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7`: hm08, all 19,158 helpers/body source IDs, GameEngine's 53 bones, one `female_sportsuit01` garment with 1,797 source vertices, four paired local targets and eight frozen recipes. Both paths use the same 23-file manifest and MPFB reference. The maximum-component tolerance was fixed at `1e-5` reference metres before comparison.

## B0: unchanged candidate algorithms

Humentity `286d33124648501535655a0de811cef55152b9fd` is compiled from the exact approved 45-file source inventory. Isolated packaging removes unused physics/dev/example dependencies and selects explicit Bevy features. Two approved local crates supply `bevy_obj 0.19.0` and `wobj 0.3.0`. CPU mesh, morph and rig algorithms are unchanged. Fresh offline resolution covers 342 packages; no unknown dependency download was needed.

The actual adapter uses Humentity loaders, `compute_target_weights`, helper deformation, Mhclo mesh jobs and CPU skeleton fitting. It emits real baked mesh morph data, skin arrays, 53 rest matrices and inverse binds. There is no replacement geometry solver. Body/garment source-ID coverage is complete: 22,077 body mesh vertices map to 19,158 IDs; 1,986 garment mesh vertices map to 1,797 IDs. Candidate outputs are produced before the comparison reads reference coordinates.

The unit/encoding adapter scales OBJ positions and MHCLO length fields by 0.1, gunzips exact targets, preserves indices/weights, and creates an identity body MHCLO from the approved base topology. Empty macro/composite containers serve exact target lookup; they do not implement world macro parameters. All raw and derived hashes are recorded. The declared raw-to-reference matrix supplies the later comparison transform.

Maximum component errors, in reference metres:

| Case | Helpers | Body mesh | Garment mesh | Joint heads |
|---|---:|---:|---:|---:|
| neutral | 4.05311584e-07 | 4.05311584e-07 | 7.58171082e-06 | 3.4570694e-07 |
| body-negative | 0.000900053978 | 0.000900053978 | 0.000794586539 | 3.4570694e-07 |
| body-half | 0.00045004487 | 0.00045004487 | 3.1876564e-05 | 3.4570694e-07 |
| body-positive | 0.000900059938 | 0.000900059938 | 6.3765049e-05 | 3.4570694e-07 |
| face-negative | 0.000900137424 | 0.000900137424 | 7.58171082e-06 | 3.4570694e-07 |
| face-half | 0.000399839878 | 0.000399839878 | 7.58171082e-06 | 3.4570694e-07 |
| face-positive | 0.000799846649 | 0.000799846649 | 7.58171082e-06 | 3.4570694e-07 |
| combined | 0.00045004487 | 0.00045004487 | 3.1876564e-05 | 3.4570694e-07 |

Neutral passes all measured geometry. Every changed body/face case exceeds the body/helper tolerance. The garment also exceeds tolerance for body cases. All fitted joint heads remain within tolerance. Rest and inverse-bind arrays are recorded and finite; their exact frame-convention parity is **NOT-RUN**. Fitted tail positions are unavailable through the public candidate API and remain **NOT-RUN**. No tail inference or substitute solver is used.

## Causal contrast

The candidate loader scales target rows by 0.1 and discards scaled deltas with squared length at most `1e-6`. A posthoc prediction from exactly those dropped raw rows explains all eight observed body/helper discrepancies with maximum residual `4.0531158440604287e-7 m`, below the fixed tolerance. See `evidence/threshold-prediction.json`. This isolates the body/helper cause; it does not predict garment propagation.

Root then authorized one bounded B1 ablation: in a separate source copy, change only `DELTA_SQ_THRESHOLD` from `1e-6` to `0.0`. The original source, B0 derived tree, binary and eight outputs remain preserved. `evidence/B1-threshold.patch` and `B1-preparation.json` record the exact change and identities. B1 is an algorithm change and its receipts say so. B1 passes all eight measured numerical cases with the same comparator, manifest, recipes and tolerance. No further semantic repair was made. Worst errors across all eight are: helpers/body `4.0531158440604287e-07 m`, garment `7.581710815385279e-06 m`, and joint heads `3.4570693963065224e-07 m`. These values come directly from `B1-comparison-bound.json`. The B0 source, adapter, binary and output hashes remain unchanged; only `src/loaders/target.rs` differs between source variants. This is a bounded causal result for the selected sample, not general readiness.

## Verification and limits

- Real native library typecheck: PASS, 149.30 s; local wefty run `run_2ee96ab4da9b8da74c5499ee614b9377` reports succeeded.
- Real CLI link: PASS, 219.70 s initial link; two adapter-only wiring corrections rebuilt in about 5–6 s. Failed executions are retained in `results/run1` and `run2`: missing `WorldSerializationPlugin`, then transient source handles released before readback. No character output or comparison pass was emitted for either failure.
- B0 actual eight-case execution: PASS, 75.76 s total, about 9–10 s per cold dev process; child peak RSS 92,536,832 bytes. These are local unoptimized research measurements, not production or browser budgets.
- B0 numerical comparison: FAIL under the fixed tolerance, as above. B1 numeric comparison: PASS for all eight cases after the isolated threshold change. Both final receipts use comparator SHA-256 `1e516a14793f387d1d7c457ea82b28deccaf72b1057f9c434146982b1478a29c`.
- B1 incremental offline build: PASS, 20.21 s; eight-case execution: PASS, 75.25 s, child peak RSS 94863360 bytes. Original B0 artifacts remain preserved.
- Comparator binding repair: ten real copied-result tamper controls PASS. The comparator now requires the full successful eight-case execution receipt and recomputes every recorded output hash before measuring. New bound receipts include execution-summary, binary, adapter, build and patch identities. Prior unbound comparison receipts are retained as historical evidence.
- Ten real `prepare_data.py` / `run_cases.py` rejection controls pass. Source/manifest/config tampering and existing-output/input aliases are rejected; all 69 approved input hashes stay unchanged. Earlier 43 handwritten preflight controls also pass. These controls are not counted as character cases.
- Native graphics, actual Web, poses, style, whole-Work exchange, rest/IBM frame parity and tail parity: NOT-RUN. Browser folder enumeration remains a known static integration gap. Only exact local targets were exercised; macro/composite domains remain outside this probe.

[ACTUAL.md](ACTUAL.md) records the artifact map and reproducible commands. [PREPARATION.md](PREPARATION.md) preserves the earlier preparation report as historical evidence; its pre-download limitations are superseded by this actual run.

VERIFIED — B0 fails the fixed numerical gate; exact dropped-row prediction isolates the body/helper cause; the single-line B1 ablation passes the same eight measured cases.

PARTIAL — native/Web graphics, poses, style, tail and rest/IBM-frame parity and Work exchange remain unverified. No new production character or dependency is admitted.
