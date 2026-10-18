# Native and Web Work exchange

The two saved Works are exact file bytes from root-observed normal toolbar
Save/Open actions. The Web file was obtained through the completed browser
download. UI actions are root-observed provenance, not inferred from stills.
`inventory.json` records relative filenames, byte counts and SHA256 values.

| File | Observed role |
| --- | --- |
| `native-ui-saved.nvwa.json` | Normal native Studio toolbar Save; schema4, revision4, skin/eyes/hair enabled |
| `web-ui-saved.nvwa.json` | Open native file through the normal Web picker, disable Hair, then normal toolbar Save/download; revision5 |
| `native-save-receipt.json`, `web-save-receipt.json` | Exact reviewed file identities and root-observed Save provenance |
| `ROUNDTRIP.json` | Root's normal-toolbar exchange record and native fresh-generation result |
| `native-return-before-report.json` | Instrumented66 observation before native return Open: generation1, exact native-saved Work |
| `native-invalid-open-retained.json` | Fresh instrumented66 capture after a normal-toolbar malformed Open: exact prior Work/body/exported CPU buffers retained |
| `native-opened-web-report.json` | Instrumented66 observation after the normal native toolbar opens the downloaded Web file: generation2, fresh body, exact Web-saved Work |
| `invalid-ui-test.nvwa.json` | **Intentionally malformed JSON negative fixture**; expected Open rejection, not a valid example Work |

Only `revision` and `character.appearance.hair` change between the two saved
Works. The first is 2743 bytes with SHA256
`dd10e51721d68a98ec06c76f3ce990e90c4763da90f6cd3848bda09033483bec`.
The return file is 2744 bytes with SHA256
`c81700d5bb404db7f9b9394ebc10f7538e72942cfc68bb6aaeca7de8c48d4ab1`.
These sizes identify files; they do not measure startup, transfer or performance.

The malformed native Open occurs before the successful native return Open.
Its parse error is visible in the corresponding [screenshot](../screens/native-invalid-normal-open.jpg).
The retained report is a successful fresh observation of valid retained state;
it is not an error acknowledgement for a bridge Open command. The returned Web
file subsequently binds skin and eyes with Hair disabled on a new native body.

Initial product Studio/Player captures use ordinary production entrypoints.
The exchange uses instrumented66 with normal production toolbar/picker actions;
the bridge observes current production bindings and does not replace Save/Open.
See the [screen labels](../screens/README.md). These GUI artifacts belong to the
frozen r4 source cohort. The later CLI-only help edit and its rebuilt/tested
receipt are separate. CPU snapshots are not GPU readback, a full asset-store
disposal audit or full visual-quality admission.

All copied text files were inspected for actual home/temp paths and common
credential patterns. Private path-bearing summaries and Save-toast screenshots
were excluded. Raw JSON and saved Work bytes were not edited or reformatted.
