# M1 CLI and GUI document equivalence

Actual prebuilt target/debug/nvwa-cli reproduces the whole native5→Web6→freshnative6 portable document. Commands reconstruct recorded visible GUI outcomes; they are not captured GUI event traces. The CLI binary was built at the41-test sequence checkpoint, before interaction changes.

| Expected revision | Shared command effect | Result revision |
| --- | --- | --- |
| 0 | 9s idle/wave/turn; IDs sequence-1/2/3 | 1 |
| 1 | smile0.34 | 2 |
| 2 | first duration3.5; starts0/3.5/6.5 | 3 |
| 3 | original9s timeline, equivalent to recorded undo result | 4 |
| 4 | restore9.5s timeline, equivalent to recorded redo result | 5 |
| 5 | jaw_width0.53 | 6 |

The bounded worker ran six individual apply calls, validate, inspect, save and entire parsed JSON comparisons. Root then replayed the [published command batch](cli-replay-commands.json) in one actual CLI call and verified the same full equality.

Run from the repository root after building the CLI:

    cargo build -p nvwa-cli --locked
    target/debug/nvwa-cli apply examples/default.nvwa.json docs/evidence/m1/cli-replay-commands.json /tmp/nvwa-m1-cli.nvwa.json
    target/debug/nvwa-cli validate /tmp/nvwa-m1-cli.nvwa.json assets
    target/debug/nvwa-cli inspect /tmp/nvwa-m1-cli.nvwa.json
    target/debug/nvwa-cli save /tmp/nvwa-m1-cli.nvwa.json /tmp/nvwa-m1-cli-saved.nvwa.json

Final and saved CLI documents equal the ENTIRE [Web revision6 download](web-sequence.nvwa.json) and [fresh native revision6 re-save](native-roundtrip.nvwa.json), including profile/hash, all parameters, IDs, durations, starts, speed and looping. Validation returned asset_checked=true, valid=true, revision=6.

After the commands above, reproduce the full parsed-JSON comparison:

```sh
python3 - <<'PY'
import json
from pathlib import Path
expected = json.loads(Path('docs/evidence/m1/web-sequence.nvwa.json').read_text())
for path in ['/tmp/nvwa-m1-cli.nvwa.json', '/tmp/nvwa-m1-cli-saved.nvwa.json',
             'docs/evidence/m1/native-roundtrip.nvwa.json']:
    assert json.loads(Path(path).read_text()) == expected, path
print('PASS entire document equality, revision', expected['revision'])
PY
```

Inverse timeline replacements model undo/redo effects; they do not establish a CLI undo/redo command. No GPU or GUI action occurred in this reproduction. Interaction and Player are outside this evidence.
