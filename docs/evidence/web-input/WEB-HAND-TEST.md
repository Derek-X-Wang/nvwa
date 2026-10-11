# User-performed repaired Web input acceptance

On2026-10-11 PDT, Derek tested the updated production preview at `http://127.0.0.1:9201/?work=works/exchanged.nvwa.json` and replied **“全部正常”** to the bundled check below.

1. Focus the Work field and enter `女娲` with a real Chinese input method. The candidate box appears; Space chooses text and inserts it once.
2. Command+A selects the field's text. Command+V pastes text.
3. Switch to another application, return, and continue typing.
4. Restart playback when checking whether candidate Space accidentally pauses the scene.

The original failure was **“无法输入中文”**, clarified as **“没有候选框”**. Root updated the production preview before this retest. Production source hashes: `web_input.rs=58655287ca544b330ecb4f1e55a36d9fc23caaee452d2e3ea3df628c39e68824`, `lib.rs=4e00f2d61a9f44439616f31c65dfca125908f29a346aca0dcfba000b0f6b5181`. Served Wasm SHA-256: `94c808dff3494647a76ccf76313368ddba64aa6e170a32c80c6e3d5bdcd72c36`.

Environment: existing Apple M2 Pro/16 GiB/macOS27.0.1 host, Codex in-app Browser. The server reports a Chrome/155.0.0.0 User-Agent; exact installed engine version, DPR and input-method name were not independently captured. The tool's production screenshot uses an ordinary1424×984 viewport; that screenshot predates the user's test.

This is attributed human acceptance. No OS keyboard trace, candidate screenshot, per-step saved JSON, browser-tab-switch test or zoom/DPR recovery result is invented. The tool callback replay, direct Unicode input, clipboard, Save/Open and native smoke have separate evidence in [ACCEPTANCE](ACCEPTANCE.md). The tool does not read or save the user's test input after the handoff.

VERIFIED — Derek reports all requested repaired Web physical checks normal. Additional browser/OS and zoom/DPR coverage remain open.
