"""Prepare an isolated input diagnostic page from the current Web package.

Run after build-web.sh; this never replaces the shipped index or Wasm.
The visible control emits a task-owned Chinese composition sentinel.
It tests installed browser callbacks, not the OS's physical input method.
"""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
bundle = root / "dist/web"
index = bundle / "index.html"
if not index.is_file():
    raise SystemExit("Build Web first: bash scripts/build-web.sh")
source = index.read_text()
if "</body>" not in source:
    raise SystemExit("Web index has no body closing tag")
(bundle / "ime-debug.html").write_text(
    source.replace("</body>", '<script src="./ime-instrument.js"></script>\n</body>')
)
(bundle / "ime-instrument.js").write_bytes(
    (root / "docs/evidence/web-input/browser-probe.js").read_bytes()
)
print("http://127.0.0.1:9201/ime-debug.html?work=works/exchanged.nvwa.json")
