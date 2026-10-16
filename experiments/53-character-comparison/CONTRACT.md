# Character foundation comparison — execution contract v1

Status: APPROVED LOCAL EXECUTION; no product admission. Owner: integration agent. Baseline: Nvwa `1a91178e894bad13bf51223b33b49cf33ea91a1c`; research `04cb9c8621c723ae31fb315730c7e8aefbcae608`.

Question: Can mature MakeHuman/MPFB character data support a small continuously editable, animated character through (A) a compiled character package or (B) an existing Rust source-data runtime? Compare the same approved sample against the same offline reference before choosing either path.

## Ownership and resource limits

- Shared contract, comparison criteria and final integration: root only, experiment 53 root.
- Download bill and provenance metadata: download worker only, `53-character-comparison/downloads/`.
- A preparation and controls: A worker only, `54-compiled-character-package/`.
- B preparation and controls: B worker only, `55-source-character-runtime/`.
- No product edits, root Cargo/lock edits, old experiment changes, GUI control or changes to the human checkout. Each experiment has an independent dependency boundary.
- At most two compilation jobs and one GPU/graphics task. No graphics task is needed for the current numeric comparison. Use only already installed/cached dependencies with network disabled; missing dependencies are a documented blocker.
- No new asset, add-on, model, library source archive, tool or binary download/install before explicit approval. Public docs, repository text/JSON metadata and HEAD requests may be read to prepare the exact bill. Do not invoke automatic asset/dependency fetchers.

## Sample classes and evidence

1. `nvwa-existing-fixture-control`: the existing original GLB, profile and authored controls only. They may prove preparation code can read real skin/morph data or reject invalid input. They do not prove MakeHuman/MPFB compatibility, mature character quality or the A/B winner.
2. `makehuman-approved-sample`: new fixed-version input files from the approved fixed bill (with explicit system-Blender amendment). Both paths must name the identical manifest digest and case IDs. Until those bytes are approved and present, report `NOT-RUN: approved sample unavailable`.
3. Handwritten tiny unit controls may test parsers and failure handling, but must be labeled as controls, never as a generated human or third-party runtime execution.

No path may substitute a preset model switch for continuous morphing, replace actual library execution with a stand-in, skip required data and report success, or count compilation as graphical/runtime acceptance.

## Common planned sample

One pinned MPFB version, one hm08 source foundation, one simple deform rig, one legal garment, one small parameter domain containing a body-proportion parameter and a local face parameter. Neutral plus two visibly different cases and one combination. Exact target names/ranges and source filenames will be derived from the approved upstream metadata; no guessed anatomy, axes, defaults or universal retarget assumptions.

Blender/MPFB is the common offline reference. A and B are both Rust execution options. No separate agent recipe-blending experiment is included at this stage.

## Result contract

Each actual case receipt records:

- `schema_version`, `route_id` (`compiled-package` or `source-runtime`), `sample_class`, `case_id`;
- exact source/input manifest hash, recipe, source package/library commit, tool version;
- `status` (`passed`, `failed`, `not_run`), actual command, exit code and log/artifact paths;
- whether the actual candidate code, native/Web graphical execution, and reference pipeline were run (separate booleans);
- coordinate/basis/unit convention and transform identity. Do not compare silently mismatched bases or infer left/right from a bone name;
- measured positions, joint/rest/inverse-bind state, garment state and any unsupported field. Missing output stays missing, not zero.

Preparation may emit a blocked receipt with missing inputs; it must not emit measured character results for a case that did not execute.

## Adoption gates after approval

Compare intermediate and extreme parameter values, mesh/joint/garment errors against the common reference, then inspect shoulder raise/elbow/knee test poses. Verify actual CLI and desktop/Web results, whole-Work save exchange, failures that preserve the original input, bounded size/time/memory and style suitability separately. Define numerical tolerances against the chosen reference before judging results. Existing M2 quality HOLD and #3/#4 boundaries stay unchanged.

No new production character or dependency is selected by preparation or by a green control suite.

## Executed reference freeze — 2026-10-16

Human approval covers the original pinned non-Blender inputs and a later Homebrew upgrade of system Blender. Original download request and manifest remain historical evidence. Blender 5.2.2 LTS is installed and has actually executed MPFB 2.0.18 offline. No standalone Blender 4.2.23 DMG was downloaded. Installation and delivery receipts live under `delivery/`.

Common manifest: `.work/character-approved-20261016/common-sample.json`, SHA256 `2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7`. All 23 input/reference files, eight case recipes, source IDs, raw-OBJ conversion and reference digests are frozen. Full source and reference arrays remain task-local, rather than being substituted with fixtures. See [exact reference and reproduction](reference/README.md).

Body capture is the complete evaluated source cage before clothing visibility MASK modifiers, including all helper IDs. Clothing is fitted by real MPFB and measured after restoring visibility masks. Numeric max-component tolerances were declared before full A/B measurements: body, joint endpoints and garment each `1e-5` reference metres. This tolerance does not cover bone roll/rest matrices, inverse-bind matrices, posed skinning, render topology, material appearance, artistic quality or performance. Missing fields remain `NOT-RUN`/unsupported and cannot pass through endpoint agreement.
