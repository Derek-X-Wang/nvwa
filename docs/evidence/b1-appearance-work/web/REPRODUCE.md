# Web CPU and file-state acceptance records

This folder contains **107 exact request/report pairs** from the running Web
experiment66 app: 104 current ready acknowledgements and three expected Open
rejections. `inventory.json` gives the byte count and SHA256 of every raw pair
and exchange artifact. `summary.json` contains the normalized checks and lists
the 54 target held source frames.

These are current entity-bound **CPU** mesh/material/image observations from
the production runtime. They are not GPU readback, screenshots, rendered
acceptance, an independent geometry oracle, continuous playback proof,
performance measurements, or a complete asset-store disposal audit. Root's
GUI observations and the separate build evidence must retain their own scope.
This evidence preparation did not run or build an app.

## What was checked

| Group | Requests | Result |
| --- | ---: | --- |
| `matrix` | 67 | Eight independent role combinations, paused Undo/Redo, nine shapes and five held global times, nominal restoration |
| `arm-endpoints` | 23 | Nine additional arm-source4 frames through shared arms-only `SetTimeline`, then original timeline/nominal shape/held1.5 restoration |
| `lifecycle` | 12 | Three rejected Opens with exact retained state, valid recovery, legacy migration, same-content new generation, native-input restoration |
| `ui-observations` | 5 | CPU observations before/after root's normal picker and Save actions |

The recipe grid is torso `-1/0/1` × jaw `0/0.5/1`. The eight-second timeline
contains arms at global0–4 and knee at global4–8. Global4 selects **knee source0**.
The arms-only supplement supplies arm source4, giving nine recipes × two clips
× source times0/2/4 = **54 held source frames**. The role combinations are checked
at the nominal recipe; the shape/time grid uses all three roles. This is not a
full role × shape × time factorial test.

`w79-r4-009/010/011` records selections7→6→7 through shared Undo/Redo. Playing
remains false and the cursor remains at1.5. Lifecycle requests02/04/06 are
explicit errors for `invalid_json`, `unsupported_appearance_asset`, and
`unsupported_character_operation`. Separate fresh captures03/05/07 exactly
match baseline01's Work JSON/hash, complete exported appearance/base state,
and captured identity. No failed request is counted as a successful old-body
capture.

Valid lifecycle Open publishes generation3, legacy Open generation4,
same-content Open generation5, and restoration generation6 after baseline
generation2. The legacy output preserves the exact schema3 content except for
schema4 and explicit `appearance:{"type":"none"}`. Skin and accessory bindings
are absent in the current snapshot. That observation does not expose the
complete CPU asset store. The restoration input is the actual native toolbar
saved revision4 file, **not** the repository example's revision2 file.

## Reproduce through visible DOM controls

Use a fresh experiment66 browser app with the already-built r4 site, assets and
`works/b1-motion.nvwa.json`. Build/export identities are in the parent evidence;
root must schedule any rebuild, server, browser or GPU work. Open the built page
with `?work=works/b1-motion.nvwa.json` and wait for the normal Studio to load.
The bridge calls the unchanged production Studio and adds a collapsible
acceptance panel.

1. Use the labelled **Acceptance command** textbox, **Run** button and
   **Acceptance report** status/pre element. Paste a raw request file's contents,
   click Run, and wait for that exact request ID. Do not invoke hidden browser
   functions or issue a second request while one is pending.
2. A successful response must have `acknowledged:true`,
   `request_succeeded:true`, `phase:"ready"`, and `current:true`. Require current
   Work/appearance/base/captured identity to agree, no preview or pending Open,
   runtime ready, and no runtime/stage/appearance errors. A stale response is not
   current success. Use a bounded55-second wait.
3. Capture `w79-pre-open`. Through the normal Studio **Open…** file chooser,
   select `exchange/native-ui-saved.nvwa.json`. Wait for ordinary file loading
   and the new B1 body, then capture `w79-after-native-open`. Require exact native
   input Work bytes/hash and a fresh generation/body. Do not accept an immediate
   capture of the retained body while file I/O starts.
4. Replay numeric request files in this order: `matrix`, `arm-endpoints`,
   `lifecycle`. For lifecycle02/04/06 require `phase:"error"`,
   `request_succeeded:false`, `current:false`, and the recorded error. Then send
   the separate fresh retention capture. Shared commands and Open staging are
   production paths, but these bridge Open requests are not file-picker proof.
5. After lifecycle12, use normal **Open…** to choose
   `exchange/invalid-ui-test.nvwa.json`. Root observed the error banner. Capture
   `w79-ui-bad-retained`; its Work, appearance, base state and identity equal
   lifecycle12. The error banner and picker action are not exported by the CPU
   report. Use normal **Open…** to select the valid native file again, then
   capture `w79-ui-recovered`; generation6→7 and exact native input bytes are
   checked.
6. In the normal Studio, clear the **Hair** checkbox. Set a new normal Work
   filename such as `web-ui-saved.nvwa.json`, and use the normal toolbar **Save**.
   Wait for the actual browser download, inspect its bytes, and capture
   `w79-web-saved-current`. **Export Work** in the bridge is not a substitute for
   normal toolbar Save. Collapse the acceptance panel for separate rendered
   inspection.

The recorded IDs fit within the bridge's128-ID launch limit. Extra startup or
unretained requests also count. Use fresh IDs or a fresh app for another run.
Entity/asset handles are launch-local; compare current binding consistency and
relative generation changes rather than requiring the original handle strings.

## File exchange boundary

Root observed normal native toolbar Save and selected that actual file in the
Web file chooser. The input is2743bytes, revision4, all roles true, SHA256
`dd10e51721d68a98ec06c76f3ce990e90c4763da90f6cd3848bda09033483bec`.
`w79-after-native-open` reports those exact Work bytes and generation1→2.

Root then observed a normal Hair checkbox edit and toolbar Web Save. The
completed browser download and its local byte copy are both2744bytes, SHA256
`c81700d5bb404db7f9b9394ebc10f7538e72942cfc68bb6aaeca7de8c48d4ab1`.
Only `revision` and `character.appearance.hair` differ semantically from the
native input: revision5 and hair false, with skin/eyes still true.
`w79-web-saved-current` reports those exact saved Work bytes. A Web
**Download started** notice alone would not establish the downloaded bytes;
the actual files are included here.

The two Save receipts are root's provenance declarations. Raw files and CPU
reports establish bytes and state; they do not by themselves prove GUI clicks,
file-picker history or screenshots. Reverse native Open of the Web-saved file
was being handled separately by root and is not claimed by this Web cohort.
Playback is session state, so comparable geometry observations require an
explicit matching held sample after Open.

## Byte integrity and publication

Raw JSON/Work files were privacy-scanned before exact copying, including nested
Work JSON strings. No home/temp paths, emails, private keys or common credential
patterns were found. No raw bytes were redacted or reformatted. Private original
summary/event files were not copied.

To check the copied byte inventory without launching an app, run this snippet
from the repository root:

```python
import hashlib, json
from pathlib import Path
root = Path("docs/evidence/b1-appearance-work/web")
inventory = json.loads((root / "inventory.json").read_text())
for name, expected in inventory["files"].items():
    raw = (root / name).read_bytes()
    assert len(raw) == expected["bytes"]
    assert hashlib.sha256(raw).hexdigest() == expected["sha256"]
assert sum(group["request_count"] for group in inventory["groups"].values()) == 107
```
