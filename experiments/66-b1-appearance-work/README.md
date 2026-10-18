# Saved appearance acceptance bridge

Completed root-run builds, actual native/Web CPU matrices and normal-toolbar file exchange are recorded in [the product acceptance record](../../docs/evidence/b1-appearance-work/RESULTS.md). The protocol and preparation notes below remain separate from that execution evidence.

This wrapper calls the unchanged `nvwa_studio::build_app()`. It installs one `Last` observer/controller. All Work commands, Open staging, fitting, materials, images, meshes and rendering stay in production. The collapsible acceptance panel sends shared commands and shows reports. It has no appearance rendering or preview state. Use the normal Studio controls to inspect the product.

The bridge is acceptance instrumentation. Native/Web compilation, actual launches, CPU observation, rendered inspection and performance remain separate evidence. The protocol does not claim GPU readback or quality admission. Clothes/M2 motion quality remains HOLD.

## Build and launch (root scheduled)

Run from the repository root. Do not start a second build while the root's heavy check is active.

```sh
CARGO_BUILD_JOBS=1 cargo build --manifest-path experiments/66-b1-appearance-work/Cargo.toml --bin studio66 --locked --offline
B1_66_COMMAND_FILE=/tmp/nvwa66-command.json B1_66_REPORT_FILE=/tmp/nvwa66-report.json target/debug/studio66 --work /absolute/path/work.nvwa.json
```

A standalone Cargo manifest normally uses `experiments/66-b1-appearance-work/target`. Set `CARGO_TARGET_DIR` explicitly when sharing the root's scheduled build target, or adjust the binary path above to the standalone target. Create the command file before launch, for example `{"request_id":"initial","action":"capture"}`. If this initial request arrives before the launch Work exists, it gets an explicit error; send a fresh capture after startup or Open a supplied Work through the bridge. The wrapper uses the production launch flags unchanged. The native asset root also uses the production resolver.

```sh
CARGO_BUILD_JOBS=1 cargo build --manifest-path experiments/66-b1-appearance-work/Cargo.toml --lib --target wasm32-unknown-unknown --locked --offline
wasm-bindgen --target web --out-dir /absolute/owned/site/pkg /absolute/target/wasm32-unknown-unknown/debug/b1_appearance_work.wasm
cp experiments/66-b1-appearance-work/index.html /absolute/owned/site/index.html
cp -R assets /absolute/owned/site/assets
cp -R experiments/66-b1-appearance-work/works /absolute/owned/site/works
```

Serve the owned site on a free assigned Nvwa loopback port. The normal Studio launch query can open a served Work file, for example `?work=works/b1-motion.nvwa.json`. This HTML exports `window.b1_66` after the Wasm start. The collapsible bridge panel has an `Acceptance command` textbox, `Run` button, readable `Acceptance report`, `Current Work JSON` textarea, and `Export Work` download button. Collapse the panel for production UI/screenshots. Native and Web include the same immutable appearance payloads from production.

## Protocol

Send one request and wait for its terminal acknowledgement before sending the next. Use a fresh `request_id` for each request, with 1–64 ASCII letters, digits, `_` or `-`. At most 128 IDs are admitted per launch. Replaying identical bytes while its acknowledgement remains current does not reapply a command. Reusing an ID after a later request, or with different bytes, rejects. A new request while another is pending rejects and cancels that pending acknowledgement; it does not undo an already applied shared command.

Native: atomically replace the UTF-8 file named by `B1_66_COMMAND_FILE`, then read `B1_66_REPORT_FILE`. The report file is replaced atomically when its content changes.

Web UI: fill `Acceptance command` with the exact request JSON and click `Run`; read the `Acceptance report` pre element. The `Current Work JSON` textarea and `Export Work` button use the current production Work. The optional programmatic interface is `b1_66.b1_66_command(JSON.stringify(request))`, then `JSON.parse(b1_66.b1_66_report())`. The command function can throw on parse rejection; its failed report is delivered on the next app tick. Current Work JSON is available as `b1_66.b1_66_work()` after a tick, including after a rejected Open.

```json
{"request_id":"skin-eyes","action":"command","command":{"type":"set_appearance","character_id":"character-1","appearance":{"type":"b1_cc0","schema_version":1,"asset_set_id":"mpfb-b1-cc0-appearance-v1","asset_set_sha256":"c3cf2b1040eed083fb1a328f0494b0c978cec42c71f3b7c826e14992f97cef04","skin":true,"eyes":true,"hair":false}}}
{"request_id":"undo","action":"command","command":{"type":"undo"}}
{"request_id":"redo","action":"command","command":{"type":"redo"}}
{"request_id":"held","action":"playback","seek_seconds":1.5,"playing":false}
{"request_id":"live","action":"playback","playing":true}
{"request_id":"capture","action":"capture"}
```

Open: `{"request_id":"open","action":"open","work_json":"<exact Work JSON text>"}`. The nested text goes through `SceneDocument::from_json` and `EditorState::request_open`, including normal B1 candidate authentication and staged replacement. It never calls `replace` directly. The command payload is the shared typed `Command`; its normal strict parser and editor transaction/Undo/Redo path apply.

The response phases are `pending`, `ready`, `error`, and `stale`. A terminal response includes `acknowledged:true`. Only `ready` with `request_succeeded:true` and `current:true` is successful current evidence. A failed request stays `error`; it cannot turn green because an older body remains valid. A successful report turns `stale` when Work, generation/body, preview, pending Open, runtime readiness/errors, or transport changes. Its completed acknowledgement remains visible, with `current:false`. During live playback, captures become stale on the next clock change; pause/seek to a held sample for durable current evidence.

A ready report includes exact current `work_json`, its hash, the production `appearance_snapshot`, and bounded hashes/counts from production `b1_frame_snapshot`. The full body arrays are discarded after hashing. Full base snapshots only support admitted B1 motion; static B1 still gets the production appearance snapshot and an explicit `NOT-EXPORTED` base-frame field. A capture checks identity before and after readback. No capture is produced while the body/appearance/Open/seek remains pending. An active editor preview rejects capture, so a preview mesh cannot certify the saved Work hash. B1 Open requires a newly published generation, including when the requested Work content is identical; canceling a candidate cannot acknowledge the retained old body. Timeout is 45 app-clock seconds. CPU capture does not measure startup or playback performance.

Null or action-irrelevant fields reject, even if an optional field would otherwise decode as absent. A malformed request, failed shared command, failed Open, production runtime error, stage error, appearance error, identity mismatch, or snapshot error gets `error` with `request_succeeded:false`. Use a new `capture` request after a failure to observe the retained valid Work/body. Native transport read/write failures are errors. This bridge intentionally has no network capture endpoint or automatic persistence beyond the two explicit native channel files.

## Verification state

Source formatting and offline lock resolution may be run by the worker. Compilation, tests, visible native/Web launch, rendered checks, cross-platform file roundtrips, and performance must be recorded by the root on the exact joint source snapshot. Do not treat this README as passed acceptance evidence.
