#!/bin/sh
set -eu
# Run only once in an owned wefty snapshot, with a dedicated output/target directory.
: "${SHOULDER80_OUTPUT:?absolute owned output required}"
: "${CARGO_TARGET_DIR:?dedicated target required}"
: "${WASM_BINDGEN:?explicit retained wasm-bindgen executable required; no download}"
mkdir -p "$SHOULDER80_OUTPUT"
python3 -B - "$SHOULDER80_OUTPUT/source-closure.json" <<'PY'
import pathlib,json,hashlib,sys
root=pathlib.Path.cwd(); names=[]
for name in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
 p=root/name
 if p.is_file():names.append(p)
for name in ['.cargo','crates','assets','vendor','experiments/79-shoulder-pose-corrective']:
 names.extend(p for p in (root/name).rglob('*') if p.is_file() and 'target' not in p.parts)
rows=[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(names))]
pathlib.Path(sys.argv[1]).write_text(json.dumps({'snapshot_cwd':str(root),'files':rows,'scope':'Exact source bytes in actual wefty execution snapshot; target is exclusive to this run.'},indent=2)+'\n')
PY
if [ -n "${SHOULDER80_NATIVE_FILTER:-}" ]; then
cargo test --offline --locked --manifest-path experiments/79-shoulder-pose-corrective/Cargo.toml --lib -j1 "$SHOULDER80_NATIVE_FILTER" > "$SHOULDER80_OUTPUT/native-test.log" 2>&1
else
cargo test --offline --locked --manifest-path experiments/79-shoulder-pose-corrective/Cargo.toml --lib -j1 > "$SHOULDER80_OUTPUT/native-test.log" 2>&1
fi
if [ "${SHOULDER80_NATIVE_ONLY:-0}" = 1 ]; then exit 0; fi
cargo build --offline --locked --manifest-path experiments/79-shoulder-pose-corrective/Cargo.toml --target wasm32-unknown-unknown -j1 > "$SHOULDER80_OUTPUT/wasm-build.log" 2>&1
"$WASM_BINDGEN" --version > "$SHOULDER80_OUTPUT/wasm-bindgen-version.log" 2>&1
"$WASM_BINDGEN" "$CARGO_TARGET_DIR/wasm32-unknown-unknown/debug/b1_shoulder_source_corrective.wasm" --target web --out-dir "$SHOULDER80_OUTPUT/pkg" > "$SHOULDER80_OUTPUT/wasm-bindgen.log" 2>&1
python3 -B - "$SHOULDER80_OUTPUT" <<'PY'
import pathlib,json,hashlib,sys
p=pathlib.Path(sys.argv[1]);rows={str(f.relative_to(p)):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in p.rglob('*') if f.is_file()}
(p/'build-receipt.json').write_text(json.dumps({'status':'native tests, offline Wasm build and wasm-bindgen succeeded','files':rows},indent=2)+'\n')
PY
