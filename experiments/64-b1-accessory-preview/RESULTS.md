# Actual B1 eyes and hair preview

The same B1 character now has an actual native and Web preview with the approved skin, low-poly eyes and short04 hair. Both platforms ran the two existing authored arm/knee clips. This is a retained experiment, **not production appearance admission**. Appearance remains temporary and is not saved in Work. Keep #79 open, #3 blocked, and #4's measurement gaps unchanged. Clothes and M2 motion quality remain HOLD.

## Observed results

| Check | Native | Web |
| --- | --- | --- |
| Offline locked compilation | PASS; 10 Rust controls also pass | PASS; actual Wasm exported |
| Actual visible launch | PASS | PASS |
| CPU sample matrix | 54/54 source checks pass | 54/54 source checks pass |
| Rendered inspection | Representative held poses, front/back and live playback | 54 held sample screenshots, front/back and live playback |
| GUI mode changes | Baseline / skin / eyes+hair restore | Baseline / skin / eyes+hair restore |
| Continuous play and shape edit | Actual arm at 1.6997s; knee at 2.3146s with edited torso | Actual arm at 1.534s; knee at 1.5474s with edited torso |
| Ordinary Save/Open | Actual Save, malformed Work rejection and reopen | Actual download, malformed Work rejection and reopen |
| Actual missing character manifest | Error, visible current body retained, exact asset restored and reopen | HTTP 404, visible current body retained, exact asset restored and reopen |
| Invalid command channel | Actual invalid UTF-8 error clears exported proof; fresh command recovers | Invalid action rejects; fresh command recovers |
| Formal runtime performance / GPU readback | NOT-RUN | NOT-RUN |

The matrix is 3 torso lengths × 3 jaw values × 2 clips × source times 0/2/4 seconds. These are actual CPU `Assets<Mesh>` arrays exported by the running app. The independent checker uses the original cage, signed MHCLO helpers and all positive final influences. Hair source IDs 82 and 195 retain five influences. It checks source/UV corner identity, ordered topology, current material/image observations and once-placed bounds. Existing 1e-5m position and 1e-6 UV guards were retained.

| Maximum component difference | Result |
| --- | ---: |
| Eyes upload versus independent skinning | 2.1732449284606048e-8 m |
| Hair upload versus independent skinning | 2.9801573209198295e-8 m |
| Native versus Web eyes / hair positions | 0 m |
| Native versus Web body positions | 3.5762786865234375e-7 m |
| Native versus Web garment positions | 2.086162567138672e-7 m |
| Native versus Web 53 bone matrix components | 4.76837158203125e-7 |

Process-local publication serials differ in 45 matched pairs because collection order differs. Source clip, source time and shape match. Entity/asset handles and document revision are process identities, not geometry comparison keys. Normal deltas are observations only; no MPFB smoothing or tangent parity is established.

In both platforms, the entire core snapshot is equal across four held appearance states. Native's temporary observation camera changes in the last state; only core snapshot equality is claimed there. Original material and absent body UV/texture state restore. Reopen and recovery replace generation 1 → 2 → 3 and rebind accessories to the new actual body. The native session initially opened the actual Web Save. Later saves retain shape, authored timeline and stage; they contain no preview appearance or camera override fields.

## Provenance and failure controls

See [evidence](evidence/README.md) for compact results, source/artifact hashes and six unmodified Web screenshots. Native original images were independently reviewed locally and are omitted publicly because they show local filesystem paths; their hash inventory does not substitute for publicly inspectable pixels. Full arrays and raw channel observations remain in the task's retained local evidence; they are not committed. The public verifier can check newly exported records without those historical files.

Rust/HTML/lock inputs are the reviewed r4 build. The r5 source map changes only two noncompiled Python sink files: actual baseline/skin captures revealed that the full record uses `null` while the compact record can use exactly `{"accessories":null}`. The sink now accepts those explicit empty representations and rejects residual payloads. Original raw bytes remain unchanged. The build receipts still authenticate all compiled input bytes. Merge integration preserved those bytes and main's PR #81 native evidence.

The public checker passed 44 artificial rejection controls and public CLI failure cases. The sink passed nine parser/store tests and a separate 32-capture-cap check. The relocated collector passed 14 artificial file-pipeline controls. These test counts are separate from actual application verification.

The initial extra Web mode capture is excluded from the 54-case matrix because its original Store receipt was not saved separately. Native recovery `n64-channel-recovered-01` is a preserved failed r3 collector attempt: it read an unchanged error from before dispatch too early. The application recovered. Collector r4 waits only for that exact old error, still fails new errors and persistent timeouts, and passed a fresh actual error/recovery cycle as `n64-channel-recovered-02`. Neither excluded record is counted as a passed matrix capture.

## Remaining admission gates

- Hairline and crown edges/shading remain visibly experimental. Mask(0.5) discards partial alpha; this is not MPFB shader parity.
- Eyes need appearance and eyelid evaluation. These fixed clips do not exercise authored head motion, gaze or blinking. There is no hair physics or collision claim.
- Native's collapsed experiment title truncates the end of the unsaved warning. The expanded panel explicitly says appearance is temporary. Improve this before production UI admission.
- Appearance identity and assets are not persisted or exchanged as part of Work. The successful Save/Open checks cover the ordinary Work contract and transient preview rebind only.
- Same-producer request/report/frame and bone consistency do not prove independent current-world freshness. Screenshots do not constitute GPU buffer readback, and the 54 native CPU records are not 54 native pixel checks.
- No formal FPS, first frame, cold start, GPU memory, DPI, additional platform or full visual quality acceptance is added.

## Reproduce with existing approved dependencies

No model or new asset download is required. The offline build requires cached dependencies, Rust 1.95.0 and an existing matching wasm-bindgen 0.2.129 executable. Missing prerequisites fail offline; obtaining new files is a separate decision.

```sh
REPO="$PWD"
OUT="$REPO/.work/appearance64/repro-build"
wefty exec --detach --max-runtime 70m -- python3 -B \
  experiments/64-b1-accessory-preview/build/build.py \
  --out "$OUT" --wasm-bindgen /ABS/EXISTING/wasm-bindgen-0.2.129
```

The output path must be absolute and new. One job builds Web then native and runs Rust controls. The retained build took 14m10s for Web compilation and 16m25s for native compilation; these are build durations, not product performance measurements.

After successful export:

```sh
NVWA_ASSET_ROOT="$OUT/web/assets" "$OUT/native/studio" \
  --work "$OUT/web/works/b1-motion.nvwa.json"
mkdir -p "$REPO/.work/appearance64/repro-captures"
python3 -B experiments/64-b1-accessory-preview/build/serve.py \
  --site "$OUT/web" --captures "$REPO/.work/appearance64/repro-captures" --port 9279
```

Run the native app and server separately. Use a free assigned Nvwa port. Open `http://127.0.0.1:9279/?work=works/b1-motion.nvwa.json`, enable eyes/hair and use the exact-frame controls. The sink allows 32 records per owned capture directory; split the 54 cases across directories rather than weakening the cap. See [native collection](collection/README.md) and [source checks](verification/README.md) for immutable export and verification commands. All probes wrap the same production Studio and B1 runtime; root dependencies, the normal Studio entry points and character assets are unchanged.
