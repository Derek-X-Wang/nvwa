#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
lab=experiments/58-b1-desktop-web
work="$PWD/.work/b1-pose-viewer"
if [[ -n "${B1_CI_INPUTS:-}" ]]; then
  python3 "$lab/prepare.py" --ci-inputs "$B1_CI_INPUTS"
else
  python3 "$lab/prepare.py"
fi
case "${1:-native}" in
native)
  cargo build --manifest-path "$lab/Cargo.toml" --offline --locked -j 1
  app="$work/Nvwa B1 Pose Lab.app"
  mkdir -p "$app/Contents/MacOS"
  cp "$lab/target/debug/b1-desktop-web" "$app/Contents/MacOS/b1-desktop-web"
  cat > "$app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>CFBundleExecutable</key><string>b1-desktop-web</string><key>CFBundleIdentifier</key><string>dev.nvwa.b1-pose-lab</string><key>CFBundleName</key><string>Nvwa B1 Pose Lab</string><key>CFBundlePackageType</key><string>APPL</string></dict></plist>
PLIST
  printf '%s\n' "$app"
  ;;
web)
  cargo build --manifest-path "$lab/Cargo.toml" --target wasm32-unknown-unknown --lib --offline --locked -j 1
  tool="${B1_WASM_BINDGEN:-/Users/derekxwang/Development/incubator/Nvwa/nvwa/.tools/wasm-bindgen/wasm-bindgen-0.2.129-aarch64-apple-darwin/wasm-bindgen}"
  test -x "$tool"
  b1_bindgen_version="$("$tool" --version)"
  if [[ "$b1_bindgen_version" != "wasm-bindgen 0.2.129" ]]; then
    printf '%s\n' "Expected wasm-bindgen 0.2.129, got $b1_bindgen_version" >&2
    exit 2
  fi
  "$tool" --target web --out-dir "$work/site" "$lab/target/wasm32-unknown-unknown/debug/b1_desktop_web.wasm"
  ;;
*) printf '%s\n' 'usage: build.sh [native|web]' >&2; exit 2;;
esac
