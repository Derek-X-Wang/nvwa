# M1.1 experiment contract

Authorized on 2026-10-11: run the editor-component prototype and Web build A/B in parallel, test both native and Web, then choose what deserves production integration. The milestone is **M1.1: editor experience and Web build optimization validation**. This is bounded M1 stabilization; M2 and new character/rig support remain outside scope.

## Frozen baseline and ownership

- Product source base: `11fc789e898119e0ed2b423f8a909dacb547f772`; product files equal merged main `571604f4f5caaa67b4a0af792860261cd8262cfb`. Existing 93-test acceptance is prior evidence, not a new test run.
- Use the exact existing character GLB, profile, Work schema, typed commands, history bounds and Bevy runtime. The authored clips remain authored clips.
- Root owns integration, repository dependencies, root `Cargo.lock`, milestone/issues, final builds and GUI/GPU measurement. Workers own disjoint `experiments/15-editor-components/` and `experiments/16-web-build-ab/` in separate worktrees. No worker edits production files or publishes/merges.
- Root preserves accepted native/Web binaries before candidate builds. Experimental generated workspaces and build profiles must not overwrite the preserved baseline or modify the primary source workspace.

## Editor components question

Can one pinned `craft-ui` tab/split component improve the existing inspector/timeline while keeping one Bevy loop and all editing/input behavior?

- Compare the existing panel layout with a small tab/split layout in the real Studio. Use real skin/morph/animation and existing command handlers, never mock character/state.
- Keep production Rust UI, runtime and Web input adapter. No eframe loop, React frontend, general docking/window framework or new document schema.
- Pin source identity and retain applicable licenses. Proposed third-party dependencies and experimental manifest changes require root integration before compilation.
- Layout state is session-only. Reset/lock/tab changes cannot modify Work, revision or undo/redo history.
- Test native and Web: start, real character, parameter drag -> one transaction, Undo/Redo, Save/Open and full JSON exchange; tab/split/reset; text focus/Space guards and available input checks at 1280x720 and 1024x768. Real IME and unsupported DPR actions remain separate NOT-RUN unless physically verified.

## Web build question

Does a separate size-oriented Web profile reduce the shipped download while keeping the exact current functionality and acceptable animation cadence?

- A is the frozen accepted release bundle. B is a separate experimental Web profile, initially `opt-level=s`, thin LTO, codegen-units=1; attempt fat LTO or further changes only after resource/cost evidence and a new build lease.
- Profile-only experiment: no feature removal, font subset change, character simplification, source changes or upstream application code.
- Root integrates profile values into generated experimental workspaces only. Do not edit root Cargo.toml/Cargo.lock or production scripts.
- Record source/dependency/asset hashes, toolchain, exact flags, build duration, raw bytes, deterministic gzip bytes and actual HTTP encoded-body bytes. Raw per-file caps and compressed first-screen total are separate measures. Nvwa's initial total download budget is 30 MB compressed; no hosting provider is selected here.
- Compare at the same Work, viewport/backend/browser, continuous animation and finite sequence. Proposed adoption gate: gzip first-screen total improves at least 10%; p95 cadence does not regress over 10% across the measured repeated samples; current behavior/93 tests and dual-target runs remain valid. Cadence is not GPU/display timing. Inconclusive or failed results are retained.
- Do not call warm/no-store runs cold-cache measurements. Exact first presentation, GPU time, browser memory and unavailable OS/browser cases remain NOT-RUN.

## Resource and evidence gates

- At most two heavy compilations globally; root grants each build lease. Start with one heavy build at a time on the 16 GiB Mac. No compiles during formal GPU measurements; only one Nvwa renderer/GPU experiment at a time. Never stop unrelated user processes.
- Preparation, source inspection, test design and lightweight checks can run concurrently. Workers request a build lease before cargo test/build/check/clippy or linking; no nested agents.
- Every experiment leaves REPORT.md, runnable commands, logs, source/artifact manifest, pass/fail/NOT-RUN items and adopt/reject/inconclusive verdict. Root checks primary evidence and obtains independent review before adoption.
- Tests and actual runs are required by the user's request. This overrides the generic prototype skill's no-test/mock suggestions. The narrow A/B component question overrides its broad multi-design website workflow.
- Prototypes remain on an experimental branch. Validated changes are separately implemented/reviewed before entering main. No paid API/cloud, machine-wide changes, signing/credential changes or unbounded CI.
