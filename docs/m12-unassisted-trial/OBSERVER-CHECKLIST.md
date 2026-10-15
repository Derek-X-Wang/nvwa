# Observer checklist

Keep this page and the results form from the participant. Do not use the expected observations below to guide the participant. The participant's own path and words are the evidence.

## Before the session

Do not start until every readiness item is recorded. Preparation is PARTIAL until then.

- [ ] The owner has reviewed the private artifact packet and recorded the exact source/runtime identities and package hashes.
- [ ] The session entry sheet is prepared from the reviewed packet and records the supplied native app (`NvwaAlphaTrial`), offline CLI path or command alias, Web Studio URL, repository working directory, guide path substitutions, pinned source/fixture inputs, fresh trial folder alias, and task-owned Work download destination. It contains setup information only, not product-action hints or expected results.
- [ ] The native app, Web bundle, CLI, default profile, fixture, and fresh trial Work folder are available. Record each exact file identity or hash in the results form.
- [ ] The source-input comparison, existing build/runtime receipts, native metadata change, and full package manifests have been reviewed. Treat these as reuse evidence, not a fresh build or signed attestation.
- [ ] The selected Web package is the reviewed v2 copy. Its manifest confirms zero symlinks and excludes the old `experiment-controls/` subtree. Do not use the provisional v1 packet.
- [ ] The observer-only reference Work is not shown or given to the participant. The participant starts with a fresh Work in the trial folder.
- [ ] The profile and fixture match the hashes in the package record.
- [ ] The Web bundle runs in the recorded WebGPU-capable browser. Record OS, browser, and available WebGPU status before the participant starts.
- [ ] The trial folder is empty, dedicated to this session, and cannot overwrite personal Works.
- [ ] No app, server, or browser from a previous trial is left running. Do not reuse an artifact whose source identity is unknown.
- [ ] The participant has the participant brief and the existing Alpha guide. Do not show this checklist, prior reports, expected outcomes, or saved example Works.
- [ ] The participant agrees to observation. Use a participant code; do not record a name, account, or unrelated desktop content.

If any item is false or unknown, do not begin. Record the exact blocker and leave readiness PARTIAL.

## During the session

- Do not explain a product action, identify a control, suggest a command, or complete a step for the participant.
- Do not interrupt pauses or mistakes. Record the elapsed time, current screen or file state, the participant's action, and their words.
- If the participant asks for help, pause the unassisted part and record the exact request, current screen/file state, and what point they identify. Do not treat the request alone as a usability failure. If they receive product guidance, record the exact help and mark only the affected and later tasks ASSISTED.
- Stop if the participant asks, a personal file may be overwritten, unsaved trial work is at risk, credentials or unrelated private data are exposed, the app or system becomes unstable, or the session requests software/model/dependency or unrelated-file downloads, an install, sign-in, or a machine-wide change. Saving or downloading trial-owned Work JSON files, including the guide's `.json` paths and browser `.nvwa.json` exports, is allowed for the documented task.
- Do not inject malformed files or force an error beyond the guide's documented task. The guide includes a stale-revision conflict followed by recovery; record whether the participant reaches and handles that documented step without pointing it out. Record other errors only if they occur in normal use. Mark any error-recovery condition not reached as NOT-RUN.
- Do not measure performance, GPU timing, DPR behavior, or unrelated acceptance criteria.

## Record for each task

Use the results template. Record first action, important pauses or backtracking, exact error text with private paths redacted, recovery attempts, completion, participant wording, and any assistance. Separate what the participant did from what the observer inferred.

Keep task states distinct:

- **INDEPENDENT:** completed without live product guidance.
- **ASSISTED:** completed after any live product guidance.
- **BLOCKED:** could not continue or complete.
- **NOT-REACHED:** the participant did not reach the task.
- **NOT-RUN:** the condition did not occur, including error recovery when no error appeared.

Do not convert a guided result, scripted result, or agent result into an unassisted pass.

## Observer-only evidence targets

These are observation categories, not instructions for the participant:

- Discovering the guide's entry point and identifying what to do next.
- Creating one Work, saving it, locating the saved file, and reopening that same file.
- Continuing that Work in Studio and using Player.
- Moving the same Work between native and Web paths without replacing it with a different file.
- Understanding save, load, and error feedback, and recovering if normal use produces an error.
- Any point where the participant expresses confidence, doubt, confusion, or an incorrect expectation.

Prior guided evidence reports successful native/Web handoff and a guided invalid-JSON recovery. Those are historical controls only. Do not tell the participant what those reports observed. The independent result for each task is the participant's actual behavior in this session.

## Observer-only reference points

Keep this section from the participant. The private artifact packet contains the current default profile and fixture, plus a reviewed nine-second Work copy for readback. The Work copy is not the participant's input or completion criterion. After the participant finishes or stops, use the retained packet manifest and the participant's own saved files to verify identities and record any differences. Do not use a matching reference hash as a substitute for observed creation, save, reopen, or file exchange.

The guide's stale-revision conflict is a documented step. Record the participant's actual attempt, result, and next action. Do not predict the error or recovery for them. If they do not reach that step, record it as NOT-REACHED; if no other recovery condition occurs, record that condition as NOT-RUN.

## After the session

Ask the neutral questions in the results template. Do not reveal the intended answers before recording the participant's response. Review the Work file and logs only after the unassisted attempt ends. Record the actual saved path within the trial folder, file hash, and the participant's visible observations. Keep the participant's task status unchanged if an observer later verifies a saved file.
