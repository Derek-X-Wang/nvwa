# Native CPU acceptance records

These files are exact copies of actual native experiment66 requests and terminal
reports. `summary.json` inventories each copied file by byte count and SHA256.
The three successful sequences contain 67 + 12 + 23 = 102 correlated requests:
99 ready acknowledgements and three expected Open rejections. Root separately
records one boot request, giving 103 including boot; that boot pair is not in
this folder. The first sender failure is retained separately and is outside
both counts.

This is current entity-bound CPU mesh/material/image evidence. It is not GPU
readback, rendered acceptance, an independent external geometry oracle, proof
of complete asset-store disposal, or continuous playback evidence. Ordinary
Studio Save/Open and Player observations belong to separate root evidence.
The normal native toolbar-saved file's identity is recorded in `summary.json`;
these bridge exports must not be described as toolbar saves.

## Reproduce with a fresh app

Run from the repository root with dependencies already available offline. Root
must schedule the build and the one active GPU app. These commands describe
reproduction; this evidence publication did not run them.

```sh
CARGO_TARGET_DIR=target CARGO_BUILD_JOBS=1 cargo build --manifest-path experiments/66-b1-appearance-work/Cargo.toml --bin studio66 --locked --offline
mkdir -p .work/appearance79-repro/native
printf '%s' '{"request_id":"boot","action":"capture"}' > .work/appearance79-repro/native/command.json
NVWA_ASSET_ROOT="$PWD/assets" B1_66_COMMAND_FILE="$PWD/.work/appearance79-repro/native/command.json" B1_66_REPORT_FILE="$PWD/.work/appearance79-repro/native/report.json" target/debug/studio66 --benchmark --work "$PWD/examples/b1-appearance.nvwa.json"
```

The raw executable needs the explicit production asset root above. Packaged
apps use their normal bundled asset resolver. `--work` accepts an absolute
path; `$PWD` resolves public repository-relative paths at reproduction time.
`--benchmark` keeps the app updating continuously for the acceptance channel.
It does not turn these records into a performance measurement or prove that
the character was playing continuously. Default Studio and Player behavior
was exercised separately by root.

Create the initial capture before launch. **Wait for its matching terminal
acknowledgement before sending another request.** An early capture can receive
an explicit startup error; after startup, send a fresh capture with a new ID
and wait for a ready acknowledgement. Never infer readiness from an older
report or reuse a failed request ID.

Then atomically replace the command file with each raw request, in numeric
order, and wait for that exact `request_id` with `acknowledged:true`. Accept
`phase:ready`, `request_succeeded:true`, `current:true` for successful requests.
For lifecycle rejection cases, require the recorded error and then send the
next fresh recovery capture. Do not send requests concurrently. Replay the
folders in order: `matrix`, `lifecycle`, `arm-endpoints`. The shared commands
advance revision/history; raw request IDs and reported entity handles are
launch-specific. To repeat a sequence, start a fresh app or use fresh IDs.

## What the sequences cover

- `matrix`: all eight independent role selections, Undo/Redo, nine torso/jaw
  recipes and five held global times per recipe, then neutral restoration.
- `lifecycle`: bad JSON, a forged appearance hash and B1 appearance on the GLB
  backend each reject. A fresh capture after each rejection retains the exact
  held Work, body, exported appearance/base buffers and identity. Valid Open,
  schema3 migration to explicit None, same-content Open and restoration publish
  generations 2, 3, 4 and 5 after the initial generation1 baseline.
- `arm-endpoints`: nine additional arm source-time4 samples, using an arms-only
  timeline installed through the shared `SetTimeline` command; the original
  timeline and neutral shape are restored afterward.

The saved eight-second timeline has arms at global0–4 and knee at global4–8.
Global4 selects **knee source0**, so the original five times 0/2/4/6/8 omit the
arm's final source4 frame. The supplemental sequence supplies that endpoint.
Together they cover nine recipes × two clips × source times0/2/4 = **54 held
source frames**. They do not represent 54 uninterrupted live playback frames.

`first-harness-failure` retains the initial sender's explicit
`previous request still pending; wait for terminal acknowledgement` result.
The sender failed to wait for the earlier boot request. This is a harness
sequencing failure, not evidence of a product rendering or lifecycle defect.

Private summaries with local paths were not copied. Every published raw JSON
file was inspected for home/temp paths and common credential patterns before
copying; raw request/report bytes were not edited.
