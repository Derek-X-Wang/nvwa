from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
evidence=root / "docs/evidence/viewport"
base, changed, undo=[json.loads((evidence / name).read_text()) for name in ["viewport-base.nvwa.json", "viewport-drag.nvwa.json", "viewport-undo.nvwa.json"]]
assert base == json.loads((root / "docs/evidence/m1/web-sequence.nvwa.json").read_text())
assert [value["revision"] for value in [base, changed, undo]] == [6, 7, 8]
assert changed != base
assert {k:v for k,v in base.items() if k != "revision"} == {k:v for k,v in undo.items() if k != "revision"}
print("PASS: actual viewport GUI documents preserve one-edit/one-Undo whole-document invariants")
