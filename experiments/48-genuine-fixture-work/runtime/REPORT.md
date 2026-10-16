# Retained native / Web Work exchange

The root operator ran the prebuilt native app and Web app with the experiment 48 artifact. Actual saved Work files and completed browser downloads are retained here. The offline verifier audits these retained bytes and the source cohort. It does not replay the GUI.

The source GLB is `c343f6cf47dc0a7c0b09f13ad7d21cf2706a08fb1cfdaca233f14edab02e44fc`; its profile, source Work and transformation ledger are bound by the verifier. Generated motion provenance comes from experiments 44, 47 and 48, independently of this runtime exchange. No new model run occurred.

| Stage | Revision | jaw_width | Actual retained Work SHA256 |
| --- | ---: | ---: | --- |
| Source wide f32 JSON | 0 | 0 | `7668eb7a2a2f87070500cbf49fa27d6794aa1fb83f5392b75a0ff51667cde779` |
| Native Save | 0 | 0 | `b3c7ead0e48bb584e2e52e17687e9d14280b1885703fed85d26e54cc76417b91` |
| CLI edit, native Open and Save, Web first download | 1 | 0.23 | `5da9940741b891a1b9c0d95e2c066fc9fed714b384ceda32b9abf1d5983db605` |
| Web single committed edit and completed download; native startup Open and Save | 2 | 0.62 | `ddf93976793aed949258bda8e90ae62a9100e2c686a6d8a1f2425439977854f0` |

Source-to-first-native comparison normalizes only schema-declared f32 fields. Integer fields, booleans and strings retain exact types and values. Each later transition compares the entire typed canonical Work exactly, allowing only the stated revision and jaw changes. Native revision 1 equals the first Web download byte-for-byte. The second Web download equals the returned native Save byte-for-byte. The two completed download claims come from the root observer; the corresponding files are present, rather than relying on a toast alone.

Root observed both apps seek to 1.90 seconds and Play advance to the 2.9667-second end. The native early seek image shows 0.38 seconds, not zero. The representative images were viewed during archiving. They show the genuine clip and different poses, with visible arm/torso intersection and a hand at the waist. **Motion quality remains HOLD.** No cause is assigned to source motion, mapping, weights or another stage. Exact runtime pose numbers, official decoder parity, anatomy/contact/generalrig, semantic quality and performance are NOT-RUN.

The native candidate executable hash is `bc063d68bf5009aafe7ee104bafaa317e27c9c82bbbe0a8a565d97e743272b38`; the Web Wasm hash is `648dfe770b5f903569e77fa35c5ec2a96311931dcb6878b7d2e69e526ab429c3`. The retained comparison identifies runtime source commit `7cfe171ea7d0bd2ba8e777b188e68ab9cbd85bf8`. All 54 source inputs match the retained blob IDs and are pinned by current content hashes in `source-cohort.json`. This audit verifies the current source bytes; it does not independently establish the candidate's build process. No fresh local compile was run. Hosted compilation is a separate CI gate.

Two earlier operator failures are retained privately and summarized in `observations.json`: a relative native `--work` argument was correctly rejected, and keyboard automation corrupted a path before a Save reported OS error 2. The operator then used a valid absolute temporary path. These failures do not count as passing exchange evidence. The private path-error image contains a home path and is excluded. `archive-adaptation.json` records exclusions and receipt hashes. Native source images were named `.png` but have JPEG/JFIF signatures; the archived `.jpg` names correct the extension and preserve every byte. Browser images also contain JPEG bytes. No image was edited or reconstructed.

`MANIFEST.json` enumerates every capsule file other than itself, with hashes, byte counts and real image formats/dimensions. The verifier rejects unlisted files, bad image structure, altered bindings, duplicate JSON keys, unknown fields, nonfinite values and wrong types. Mutation controls invoke the actual verifier command, refresh the changed file's manifest hash for semantic mutations, require rejection, restore the exact archive, then require a passing result. The controls run with normal Python and `-O`; no correctness check relies on `assert`.

Run from the repository root, using Python 3.9 or newer:

```sh
python3 experiments/48-genuine-fixture-work/runtime/verify_evidence.py
python3 -O experiments/48-genuine-fixture-work/runtime/verify_evidence.py
python3 experiments/48-genuine-fixture-work/runtime/test_controls.py
python3 -O experiments/48-genuine-fixture-work/runtime/test_controls.py
```

For a manual replay, use existing matching builds and provision a disposable Work copy. Supply absolute paths for both variables below. Do not overwrite the retained archive. The native binary accepts an absolute `--work` path; `NVWA_ASSET_ROOT` points to experiment 48's `artifacts/assets` directory.

```sh
NVWA_ASSET_ROOT="$ASSET_ROOT" "$NATIVE_BINARY" --work "$ABSOLUTE_WORK_COPY"
"$CLI_BINARY" inspect "$ABSOLUTE_WORK_COPY"
"$CLI_BINARY" validate "$ABSOLUTE_WORK_COPY" "$ASSET_ROOT"
```

In the native UI, select the genuine clip, seek/play and Save. Apply the retained command with `"$CLI_BINARY" apply "$ABSOLUTE_WORK_COPY" experiments/48-genuine-fixture-work/runtime/native/reload-command.json "$ABSOLUTE_WORK_COPY"`, then Open and Save in native. Serve a prebuilt Web site with the identical GLB under `assets/generated/` and that saved Work under `works/native-saved-edit.nvwa.json`. Open its URL with `?work=works/native-saved-edit.nvwa.json`. Seek/play, Save and wait for a completed download. Change jaw width to 0.62 once, Save, retain the completed download, then start native with its absolute path and Save. Re-run the scoped CLI inspect/validate on the exchanged copies. For a prepared site copy and an available port in the project's reserved range:

```sh
python3 -m http.server "$RESERVED_FREE_PORT" --bind 127.0.0.1 --directory "$PREBUILT_SITE"
```

Open `http://127.0.0.1:PORT/?work=works/native-saved-edit.nvwa.json`, replacing `PORT` with that selected port. Stop that owned server when replay ends. These are reproduction instructions, not a fresh replay performed by this archive task.

Alpha49's unassisted human trial remains separate and NOT-RUN. This guided operator exchange does not satisfy it. Root reports native sessions exited zero and no owned renderer remains; that is a retained observer claim. The archive verifier starts no processes except bounded Python control subprocesses and leaves no renderer/server to clean up.
