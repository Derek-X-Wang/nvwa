# Observer checklist

Keep this page and the results form from the participant. Do not use the expected observations below to guide the participant. The participant's own path and words are the evidence.

## Before the session

Do not start until every readiness item is recorded. Preparation is PARTIAL until then.

- [ ] The owner has reviewed the private artifact packet and recorded the exact source/runtime identities and package hashes.
- [ ] The private session entry sheet records the checked external authoring-agent session, native Studio, separate Player entry, Web Studio URL, empty trial folder and Work download destination. Its template has no active entries yet. The participant does not need build commands, source hashes or developer path substitutions.
- [ ] The native app, Player entry, Web bundle, CLI, default profile, fixture, and fresh trial Work folder are available. Record each exact file identity or hash privately in the results form. Player starts without loading a reference Work.
- [ ] The external agent is prepared with the reviewed CLI/profile, fresh output folder and developer guide. It waits for the participant request. Retain its fixed setup instructions and tool record; it must create a new Work, not copy a finished Work, operate the GUI or coach later human steps. Do not present it as a built-in Nvwa agent.
- [ ] The source-input comparison, existing build/runtime receipts, native metadata change, and full package manifests have been reviewed. Treat these as reuse evidence, not a fresh build or signed attestation.
- [ ] The selected Web package is the reviewed v2 copy. Its manifest confirms zero symlinks and excludes the old `experiment-controls/` subtree. Do not use the provisional v1 packet.
- [ ] The observer-only reference Work is not shown or given to the participant. The participant starts with a fresh Work in the trial folder.
- [ ] The profile and fixture match the hashes in the package record.
- [ ] The Web bundle runs in the recorded WebGPU-capable browser. Record OS, browser, and available WebGPU status before the participant starts.
- [ ] The trial folder is empty, dedicated to this session, and cannot overwrite personal Works.
- [ ] No app, server, or browser from a previous trial is left running. Do not reuse an artifact whose source identity is unknown.
- [ ] The participant has the revised Chinese participant brief and completed entry sheet only. Keep the developer Alpha guide with the authoring agent/observer. Do not show this checklist, prior reports, expected outcomes, or saved example Works.
- [ ] The participant agrees to observation. Use a participant code; do not record a name, account, or unrelated desktop content.

If any item is false or unknown, do not begin. Record the exact blocker and leave readiness PARTIAL.

## During the session

- Do not add live product guidance, point out a control, suggest a command or complete a human step. The written participant brief is fixed before the session. The prepared external agent may execute the requested CLI creation task only; record its output separately from human actions.
- Do not interrupt pauses or mistakes. Record the elapsed time, current screen or file state, the participant's action, and their words.
- If the participant asks for help, pause the unassisted part and record the exact request, current screen/file state, and what point they identify. Do not treat the request alone as a usability failure. If they receive product guidance, record the exact help and mark only the affected and later tasks ASSISTED.
- Stop if the participant asks, a personal file may be overwritten, unsaved trial work is at risk, credentials or unrelated private data are exposed, the app or system becomes unstable, or the session requests software/model/dependency or unrelated-file downloads, an install, sign-in, or a machine-wide change. Saving or downloading trial-owned Work JSON files, including the guide's `.json` paths and browser `.nvwa.json` exports, is allowed for the documented task.
- Do not inject malformed files or force an error. The developer guide retains a stale-revision reproduction exercise; it is not a required human task in the revised brief. Record normal-use errors and actual recovery attempts. If the authoring agent handles a CLI error, record agent recovery separately; do not credit it as human recovery. Any human recovery condition that does not occur is NOT-RUN.
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

- Understanding the Chinese task and finding the supplied task entries without live help.
- Personally requesting creation of a new Work through the prepared external agent, then saving, locating and reopening that same Work. Record the CLI creation as agent execution, not manual human CLI use.
- Continuing that Work in Studio and using Player.
- Moving the same Work between native and Web paths without replacing it with a different file.
- Understanding save, load, and error feedback, and recovering if normal use produces an error.
- Any point where the participant expresses confidence, doubt, confusion, or an incorrect expectation.

Prior guided evidence reports successful native/Web handoff and a guided invalid-JSON recovery. Those are historical controls only. Do not tell the participant what those reports observed. The independent result for each task is the participant's actual behavior in this session.

## Observer-only reference points

Keep this section from the participant. The private artifact packet contains the current default profile and fixture, plus a reviewed nine-second Work copy for readback. The Work copy is not the participant's input or completion criterion. After the participant finishes or stops, use the retained packet manifest and the participant's own saved files to verify identities and record any differences. Do not use a matching reference hash as a substitute for observed creation, save, reopen, or file exchange.

The developer guide's stale-revision exercise remains a separate reproducibility check. Human error recovery is evaluated only when a condition occurs during the participant task; otherwise it is NOT-RUN. Preserve the original help request and guided follow-on as historical evidence, not results of this revised protocol.

## After the session

Ask the neutral questions in the results template. Do not reveal the intended answers before recording the participant's response. Review the Work file and logs only after the unassisted attempt ends. Record the actual saved path within the trial folder, file hash, and the participant's visible observations. Keep the participant's task status unchanged if an observer later verifies a saved file.
