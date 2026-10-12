# First hosted CI receipt

2026-10-12. [Run38278869611](https://github.com/Derek-X-Wang/nvwa/actions/runs/38278869611), attempt1, completed successfully. Tested PR #35 head `fef9ad3955a71a00ccc5b4266fba13a072fc335d`; actual checked-out PR merge `2ead1b1ca72ebbde5e1dd959a4fda5d1cb138d62` combines that head with base main `de4ddefab91d21dc6f6d4b81a07b0434fa619273`. These exact identities differ from the branch storing this receipt; no merged-main result is claimed.

| Standard runner | Actual result | Time |
| --- | --- | --- |
| Ubuntu24.04 x64 | Format, strict core/CLI Clippy,27 core/CLI tests,72 Python plus5 Node diagnostic tests and two collector controls pass |37 seconds |
| macOS14 ARM64 |103 workspace CPU tests, normal native workspace check and actual studio Wasm-target library compilation pass |30m10s, below45-minute limit |

All Rust result counts show zero failed, ignored or filtered. The portable27 are a subset of the workspace103. Mac test compilation took23m35s, native check2m41s and Wasm check3m31s. Logs confirm Rust1.95.0, one Mac/two Ubuntu Cargo workers, incremental disabled and reduced-debug profiles. No cache or artifact upload step ran.

Fresh independent R2 review checked both actual logs, identities, commands, profiles and counts. It refetched the public Mac log and found identical bytes: SHA256 `a648d25c6dd110116a0b8596b7c620ef76dce4e8addc77089e20fa7be38ac9b2`. No compiler warnings/errors or actionable findings. The sole annotation is a notice about possible macOS queue delays, not an execution failure.

[Receipt and raw-log hashes](receipt.json), [run/steps metadata](run.json), [API identity](api-identity.json), [Ubuntu full log](ubuntu.log), [Mac full log](macos.log). Raw logs retain terminal control sequences. The complete local/hosted record is published without pushing another commit to the already-tested CI head, which would launch another cold run.

VERIFIED — One actual successful hosted cold trial of the bounded CPU/compile pipeline. PARTIAL — CI remains proposed in PR #35 until merge. NOT-RUN — A merged-main receipt, peak RAM/disk, future-run timing guarantees, native/Web startup/pixels, physical IME/DPR, GPU, performance, JS packaging and Wasm execution.
