# M1.1 acceptance and adoption decision — 2026-10-11

Two isolated native subagents prepared the component and profile experiments; a third independent cross-model reviewer audited code and raw evidence. Root owned dependency/lock integration inside generated workspaces, build leases, all GUI/GPU work and publication. Four concurrent workflows were available; one heavy compile ran at a time on this16GiB Mac. Formal measurements used one Nvwa renderer with no task compile. Production source, root Cargo.toml and Cargo.lock remain unchanged.

## Decisions

| Candidate | Result | Next action |
|---|---|---|
| Pinned craft-ui tab/resize controls, app-owned session layout | Narrow pattern selected; available native/Web behavior passes | Separate production wrapper/integration review; finish native small-window and physical input checks |
| `web-size`: opt-level=s, thin LTO, one codegen unit |12.1964% smaller; runtime INCONCLUSIVE | Retain candidate, defer default adoption; bounded quieter follow-up |

Do not transplant PhotoCraft's application, eframe loop or a general docking framework. No M2 model/weight/provider work was added. Authored idle/wave/turn clips remain authored.

## Verification

- Original frozen workspace:93 tests pass,11.31s build plus tests. Component overlay:99 tests pass, including a real idle resize regression demonstrated red/green, actual tab/resize controls, current-frame pointer/Space guards at both required sizes and complete Work/history preservation.
- Component native release build280.34s; Wasm build19.58s / packaging total32.20s. One pinned craft-ui package added in the generated lock; one egui0.36.2 instance. Pinned MIT notice retained. Current source/lock/native/Wasm identities are in experiment15 evidence.
- Native component actual startup: visible real rig at1280×720 logical /2560×1440 content scale2. Layout actions preserve all Work fields and history. Derek physically confirmed continuous jaw drag plus one Undo returns0.71, and split resize/Escape restore works. Root saved rev3 before/manual rev5 after: only revision differs. Redo/reload fully equal at rev6. Native1024×768 actual GUI remains NOT-RUN.
- Web component actual startup/operations at1280×720 and1024×768: real skin/morph/animation; one jaw drag makes one revision, Undo/Redo preserve full content except monotonic revision; tab/split/lock/reset never change Work. Timeline scrolling exposes all transport/sequence controls. Native→Web rev6 and Web→native rev8 three-action/9s Work compare fully equal. Physical IME/DPR are NOT-RUN for this new prototype; unchanged adapter's earlier physical acceptance is not promoted to new evidence.
- Web size candidate: Cargo596.88s, packaging9.81s, sampled owned aggregate RSS peak1,579MiB; all45 frozen product inputs, tool, static content, Work and GLB remain exact. Raw Wasm85,583,469→75,582,774B; first-screen gzip20,539,196→18,034,148B. B passes the size gate. Individual raw-file hosting limits remain a separate unresolved selection.
- Original native and both Web arms actually start with the real character. Both Web arms perform drag/Undo/Redo, save/reload/full-JSON native exchange and click-triggered authored wave. Reopening Work intentionally starts a new asset generation; the functional B log therefore contains a second GLB retrieval. This is not a duplicate initial download. Formal navigation logs each contain exactly one GLB body.
- Native fresh15s rerun: Metal,1280×720 scale1,600 samples, p95 main-loop18.5903ms, fresh visible humanoid PNG confirmed by root and independent reviewer. Earlier all-black capture stays FAILED, retained and excluded. Raw screenshot with a local path in its UI stays local; public report labels host paths.
- Web formal order A1,B1,B2,A2,A3,B3, same Chrome155 IAB/BrowserWebGpu,1280×720 scale1, same no-store gzip handler/port and fixed Work. Twelve runs each report600 samples, correct18joints/9skins/4morphs and no error. Continuous idle keeps playing; each Player sequence ends at9s/turn, editor hidden. Finite samples at~15s mix active motion and the completed held pose; they are not motion-only cadence.
- Median p95: idle18.8→20.1ms(+6.91%); finite+held19.5→18.9ms(-3.08%). Two paired breaches are retained: idle pair2+11.17%, finite pair1+10.50%. The conservative all-pair10% gate does not pass. Three repetitions and sample variability do not establish causation or statistical equivalence. Default stays unchanged.
- Separate Python HTTP receipts match raw/gzip hashes. Browser-UA request inventory and server body writes agree with each frozen first-screen total and Player+523B. These are not browser/TCP receipt proof. Original optional `.meta` requests and all rejected/repeated functional request data are preserved.

PARTIAL —93 original/99 overlay tests, dual-target builds, real GUI operations, human native drag/Escape, complete two-way Work exchange and bounded A/B evidence pass within the stated scope. Native1024 GUI, new physical IME/DPR, navigation-to-ready timing, cold cache, exact first presentation, GPU/display time, browser memory and additional platforms remain NOT-RUN. No main promotion occurred.

## Artifacts and runnable commands

Public evidence contains path-labelled text copies, actual unaltered component/Web screenshots, saved Work, HTTP logs, raw runtime JSON and comparison arithmetic. `MANIFEST.json` records public-file hashes; exact originals and binaries stay task-owned under `.work/m1-1` in the primary checkout. No raw binary/cache is committed.

Run from the primary checkout on this Mac:

```sh
cp -n examples/default.nvwa.json .work/m1-1/ui-preview.nvwa.json
open .work/m1-1/ui-candidate/Nvwa-M11.app --args --work "$PWD/.work/m1-1/ui-preview.nvwa.json"
python3 -m http.server 9201 --bind 127.0.0.1 --directory .work/m1-1/ui-candidate/web
```

Open `http://127.0.0.1:9201/`. The first native prototype defaults to A; select B · Components to compare. The simple preview serves raw bytes; use experiment16's observed gzip server for measurement. Its request-log path must be new for each invocation. Profile B is preserved at `.work/m1-1/web-size/web`; accepted A at `.work/m1-1/baseline/web`. Do not run both renderers during formal measurement.

Original tests and prototype reproduction:

```sh
CARGO_BUILD_JOBS=2 cargo test --workspace --locked --offline
python3 -B experiments/15-editor-components/prepare.py
cp experiments/15-editor-components/generated-manifests/Cargo.lock .work/m11-ui/generated/Cargo.lock
cp experiments/15-editor-components/generated-manifests/nvwa-studio.Cargo.toml .work/m11-ui/generated/crates/nvwa-studio/Cargo.toml
python3 -B experiments/15-editor-components/run-stage.py tests --lease MANUAL_UI_REPRO
python3 -B experiments/15-editor-components/run-stage.py native --lease MANUAL_UI_REPRO
python3 -B experiments/15-editor-components/run-stage.py wasm --lease MANUAL_UI_REPRO
```

Preparation refuses overwrites; alternate prepared workspaces require `--workspace` on every stage. Reproduction assumes the pinned dependencies/toolchain/wasm-bindgen are already installed/cached, as on this host. Fresh environments must fetch the pinned dependencies. Build scripts use the primary shared cache without deleting it.

Web profile reproduction requires the preserved byte-identical accepted A and pinned tool; rebuilding A cannot claim the same binary hash. Follow [experiment16](../../../experiments/16-web-build-ab/README.md). Recompute public matched data into a new output/evidence directory; `summarize-matched.py` refuses to overwrite previous slices/results. An experiment conclusion may be INCONCLUSIVE while its bounded investigation is complete.

## Review and retention

Independent cross-model review repaired actual idle-height clamping and bounded owned-process cleanup; final source/artifact/JSON/arithmetic/screenshot audit found no unresolved blocking issue. Review separately confirmed the finite held-pose sampling limitation. [Review record](REVIEW.md).

Root copied reviewed source, lock, all required ignored candidate bundles and exact raw evidence to the primary checkout before managed worktree archival. Root-owned previews/renderer processes are closed at handoff; temporary viewport override is reset. Shared target cache is retained.
