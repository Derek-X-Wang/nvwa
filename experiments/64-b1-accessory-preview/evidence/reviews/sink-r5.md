# Capture sink targeted re-review — r5

**CLEAR for the narrow Python sink compatibility fix.** The sink now accepts the two explicit empty-runtime representations without accepting residual attachment evidence. This does not validate a running HTTP server, browser Store action, native app, rendering, or geometry.

Verified file hashes:

- `experiments/64-b1-accessory-preview/build/serve.py`: `cc044dc371360026b68bd110e20b4a630733d662903b7718d56e4d4d026801b3`.
- `experiments/64-b1-accessory-preview/build/test_serve.py`: `6b89454f25350b1bfb44f88706aeac94f235471ce34c1a3ad0914c7291a113a1`.

Compared the server to `.work/appearance64/server-r4-backup/serve.py`. The only implementation changes are `empty_runtime` at lines 27-29 and its non-accessory-mode check at line 71. The helper accepts only JSON null or a dictionary whose exact key set is `{'accessories'}` and whose value is null. Both full and compact observations must explicitly contain `accessory_runtime` and independently satisfy that rule. Missing fields, empty dictionaries/lists, false, strings, empty accessory lists, nonempty rows, and residual generation/identity fields reject. Accessory-mode identity/rows validation remains unchanged.

The function returns the original parsed envelope without replacing either representation. `CaptureStore.save` still writes the original raw bytes with exclusive creation, hashes those same bytes, refuses overwrite, and enforces the existing 32-capture cap. Raw records are not normalized to make the check pass.

Independently executed all **9 current parser/store tests** against the actual implementation using `python3 -B`, with temporary fixture directories redirected to the existing authorized review scratch directory. Result:

```text
Ran 9 tests in 0.006s
OK
```

Coverage includes baseline/skin/full+compact combinations of both empty representations, malformed/missing/residual rejections, unchanged accessory identity rejection, actual-store byte/hash preservation, duplicate refusal, and no-write on invalid input. Also exercised the actual store limit separately: 32 distinct valid records were saved; the 33rd returned 409 and created no additional file. All fixture directories were removed on completion; no HTTP server was started.

All 13 files in the r4 source manifest were checked: only the two named Python files differ. Rust, HTML, lockfile, and other frozen entries still match r4. Root must retain the compiled-artifact identity as r4 and separately record this noncompiled sink revision; this review does not relabel the old build as an r5 build.

Integration note, outside this sink verdict: the separately reviewed native collector r2 still requires non-accessory `accessory_runtime` to be `None` in both report and frame (`collection/collect_native.py:167-168`). It will reject the now-confirmed compact `{'accessories': null}` representation. Root was notified; no collector edit or broader review was performed here.

VERIFIED — two exact hashes, bounded source diff, 9 actual parser/store controls, actual 32-record cap, and unchanged remaining r4 entries. NOT-RUN — real browser Store recovery, HTTP service, native app, build, GUI, GPU, or numerical checker. Only this report was written permanently; no task-created processes or fixtures remain.
