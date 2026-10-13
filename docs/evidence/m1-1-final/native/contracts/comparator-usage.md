# Private comparator usage

Whole-Doc file comparison only. Root must independently observe real native GUI behavior. Self-controls use synthetic in-memory documents and input files; they are not product tests or native acceptance.

From the assigned checkout:

```sh
python3 -B .work/m11-native-acceptance/contracts/compare_native_doc.py --case same --actual .work/m11-native-acceptance/contracts/native-same-saved.nvwa.json --receipt .work/m11-native-acceptance/contracts/same-saved.receipt.json
python3 -B .work/m11-native-acceptance/contracts/compare_native_doc.py --case other --actual .work/m11-native-acceptance/contracts/native-other-saved.nvwa.json --receipt .work/m11-native-acceptance/contracts/other-saved.receipt.json
python3 -B .work/m11-native-acceptance/contracts/compare_native_doc.py --case other --actual .work/m11-native-acceptance/contracts/native-other-reloaded-saved.nvwa.json --receipt .work/m11-native-acceptance/contracts/other-reloaded.receipt.json
python3 -B .work/m11-native-acceptance/contracts/compare_native_doc.py --case other --actual .work/m11-native-acceptance/contracts/native-other-after-interaction.nvwa.json --receipt .work/m11-native-acceptance/contracts/other-interaction.receipt.json
```

Actual input paths may instead point to root's actual GUI output location. Receipt writes are restricted to this private contracts directory. Exit 0 means whole-Doc equality; exit 2 means failure. Missing actual files return FAIL and execution NOT-RUN, with no invented actual hash. Valid actual files report SHA-256, bytes, equal flag, mismatch count and JSON Pointer fields. Diffs are limited to 64 entries, with a truncation flag.

Inputs are checked against manifest hashes. Every object's exact key set and every array's order/length are compared. String/bool/integer types stay strict. Decimal-to-binary32 conversion is exact round-to-nearest/ties-even without a binary64 intermediate or epsilon; only manifest f32 paths use this rule. NaN/infinity, overflow to binary32 infinity, duplicate keys and invalid UTF-8 fail. Negative zero remains distinct from positive zero. Actual file reading is bounded at 2 MiB + 1 byte.

The original comparator-controls receipt and byte-identical pre-fix copy retain the prior 24 green controls. comparator-controls-v2 covers 29 controls: the original 24 plus five actual CLI/JSON cases for -0, -0.0, positive integer zero, equal binary32 decimal spelling and a changed binary32 value. The JSON parser preserves lexical -0 as Decimal negative zero; ordinary integer fields remain strict integers. negative-zero-cli-red retains the old incorrect PASS/exit 0 on signed zero; negative-zero-cli-green correctly returns FAIL/exit 2 with the same input hash. signed-zero-repair-summary links the exact preserved identities and result. comparator-same-file-control and comparator-other-file-control compare fixture files to themselves only. comparator-current-output and comparator-current-output-v2 record the missing real reloaded output before/after the repair; both are FAIL/NOT-RUN. None of these receipts substitutes for GUI evidence. No Cargo, GPU, UI, product test, signing or publication ran.
