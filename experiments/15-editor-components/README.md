# M1.1 editor component experiment

Question: can one pinned craft-ui tab/split improve the real Studio while preserving editing and input behavior? This is a throwaway overlay on frozen source `11fc789e898119e0ed2b423f8a909dacb547f772`.

Prepare from this experiment worktree:

```sh
python3 experiments/15-editor-components/prepare.py
```

The command refuses to overwrite an existing workspace. For another copy, use `--output .work/m11-ui/generated-2` and pass `--workspace .work/m11-ui/generated-2` to every stage command. It writes original source/asset hashes and overlay hashes to the adjacent `*-manifest.json`. It does not edit or resolve dependencies. Root adds `dependency-proposal.toml` to the generated Studio dependencies and generates the lockfile. Root approved the exact pinned dependency on 2026-10-11. The exact root-approved generated manifests are retained for offline reproduction; after preparation, apply them with:

```sh
cp experiments/15-editor-components/generated-manifests/Cargo.lock .work/m11-ui/generated/Cargo.lock
cp experiments/15-editor-components/generated-manifests/nvwa-studio.Cargo.toml .work/m11-ui/generated/crates/nvwa-studio/Cargo.toml
```

Use the matching destination for an alternate prepared workspace. Stage metadata records that workspace, its matching preparation manifest, and hashes of its actual source and lock.

After root grants a build lease, this entry point captures logs, applies a 30-minute cap, and preserves successful artifacts before the next build:

```sh
python3 experiments/15-editor-components/run-stage.py tests --lease <active-root-lease>
python3 experiments/15-editor-components/run-stage.py native --lease <active-root-lease>
python3 experiments/15-editor-components/run-stage.py wasm --lease <active-root-lease>
```

Equivalent exact Cargo commands from the generated workspace:

```sh
CARGO_BUILD_JOBS=2 cargo test --workspace --locked --offline
CARGO_BUILD_JOBS=2 cargo build -p nvwa-studio --release --locked --offline
CARGO_BUILD_JOBS=2 cargo build -p nvwa-studio --lib --release --target wasm32-unknown-unknown --locked --offline
```

Use a separate shared Cargo target directory chosen by root. The `wasm` stage packages directly with the existing exact wasm-bindgen0.2.129 executable. It copies the unchanged Web entry/assets/Work example and font/craft-ui licenses. Root owns arranging its tool path; `--tool-path` can select an existing executable. Do not install tools or launch GPU processes from the worker.

Root launches native with a task-specific Work path. The default prototype path is `.work/m11-ui/component-work.nvwa.json`; ensure the directory exists. The Rust toolbar switches between A (existing panels) and B (craft components). The B inspector has visible Shape and Profile tabs. Shape contains all existing sliders, preview hint and Reset shape command. Profile contains the same source/license details. Reset layout returns to Shape. The timeline handle resizes its split; Lock split prevents resizing; Escape during a split drag restores its starting height. Timeline controls remain reachable through horizontal/vertical scrolling in B. Layout is session-only and does not persist into a Work.

The same frozen existing command handlers perform real edits, single-transaction preview commits, Undo/Redo, and Save/Open in both variants. The viewport remains unpainted and the same current-frame pointer and text/Space/Undo guards remain in use. Layout is cloned per UI pass and accepted only after egui's final pass, so discarded passes do not accumulate layout deltas.

Acceptance belongs to root: real native/Web at 1280×720 and 1024×768, parameter drag one revision, Undo/Redo, full JSON Save/Open exchange, timeline, tabs, split, lock/reset/cancel, keyboard/clipboard/input guards. Physical IME and unsupported DPR are NOT-RUN unless root provides physical evidence. Compile and headless egui tests do not prove native/browser functionality or performance.
