# CLI third-entry evidence

This record proves the existing native CLI file workflow on the Nvwa base source cohort. It used the bundled profile and real fixture asset. The command batch sets `jaw_width` to `0.5` and adds the discovered `idle` clip. Both are authored data; no generated action is claimed.

The exact six calls, arguments, exit codes, stdout and stderr are in [receipts.json](receipts.json). The [command batch](commands.json) and complete [saved Work](authored-work.nvwa.json) are retained as standalone files. All recorded paths are project-relative. The final `inspect` JSON was parsed and compared in full with the saved Work. `validate` returned `valid: true`, `asset_checked: true`, at revision 2.

The runtime replay reused a prebuilt CLI binary with SHA-256 `eb2a198cfbae38c499a67925563a35db9566a4a13201e309540af955ff130202` and did not run a fresh build at this stage. The binary hash matched the earlier private receipt. The CLI and core source trees, workspace manifest, lockfile and toolchain file match source head `8dfc8a8c05ac2f5794498a76b36e8c747e27054c`; their object IDs are recorded in `receipts.json`.

## Reproduce from source

From the repository root, use the pinned Rust 1.95.0 toolchain and lockfile. This reproduction builds from source; the archived runtime replay above used the prebuilt binary.

```sh
cargo build --locked -p nvwa-cli
mkdir -p .work
OUT="$(mktemp -d .work/cli-third-entry.XXXXXX)"
CLI="$PWD/target/debug/nvwa-cli"

"$CLI" new assets/character.profile.json "$OUT/initial.nvwa.json"
"$CLI" describe-capabilities "$OUT/initial.nvwa.json" > "$OUT/capabilities.json"
cp docs/evidence/cli-third-entry/commands.json "$OUT/commands.json"
"$CLI" apply "$OUT/initial.nvwa.json" "$OUT/commands.json" "$OUT/edited.nvwa.json"
"$CLI" validate "$OUT/edited.nvwa.json" assets
"$CLI" save "$OUT/edited.nvwa.json" "$OUT/authored-work.nvwa.json"
"$CLI" inspect "$OUT/authored-work.nvwa.json" > "$OUT/inspect.json"
python3 - "$OUT/authored-work.nvwa.json" "$OUT/inspect.json" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    saved = json.load(f)
with open(sys.argv[2]) as f:
    inspected = json.load(f)
assert inspected == saved
print("complete Work readback matches")
PY
```

The replay needs no Studio, browser, GPU, motion model or model weights. The base CI run [38790750484](https://github.com/Derek-X-Wang/nvwa/actions/runs/38790750484) passed on `8dfc8a8c05ac2f5794498a76b36e8c747e27054c`; that run is base evidence only. Candidate and final-main CI remain separate pending checks. This record does not validate Windows, other Linux distributions, rendering, or generated motion.
