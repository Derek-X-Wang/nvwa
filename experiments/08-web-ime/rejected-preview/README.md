# Rejected inline-preview adapter evidence

`web_input.rs` is the exact frozen production source at SHA256 `4db492ca19e7755a8849a1dd8a8146351afa57d37d718a95ac22e3a2462b24b5`. `lib.rs` is its corresponding source at `8dca0482f4ef87c94376b6199e11a7ae7215511386ac3da7fb8ee04a22315c7e`. The coordinator copied these from its readonly review packet; the worker does not modify them.

```sh
python3 experiments/08-web-ime/rejected-preview/run_probe.py
```

Expected/actual exit **101**: the nine frozen tests pass; two additional real-egui selection regressions fail. Cmd+A → Preedit → cancel leaves empty instead of `path`. Commit女娲 → Cmd+A → next Preedit → cancel leaves empty instead of `path女娲`. Exact stdout is `run-output.txt`; source/compiler/rlib/commands are in `linked-artifacts.json`. This compiles only the tiny test crate using coherent cached native rlibs, without Cargo dependency builds or network access. Generated source/binary are ignored.

The coordinator's earlier 68-test workspace result did not cover these selection cases. It is valid evidence for its tested assertions, not acceptance of the rejected preview adapter. The older direct real-egui preedit/cancel tests remain here and in the original probe as historical evidence that egui inserts uncommitted preview into the caller's String. They are not the final adapter's emitted event contract.

The final production adapter keeps uncommitted text in the browser/OS IME and sends confirmed commit only. Its tests preserve the same required canonical text/selection outcomes and use the actual production reducer emissions. The final green command is `python3 experiments/08-web-ime/run_rework_regressions.py`.

NOT-RUN — OS/CUA physical composition delivery. These are real-library injected-event regressions, not browser/physical acceptance.
