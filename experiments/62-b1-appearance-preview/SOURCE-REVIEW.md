# Independent source review — experiment62

Fresh native Codex reviewer `appearance62_review`, GPT-6 Astra/high. Preview and asset implementers used GPT-6.1 Sol/high in separate worker sessions; root integrated build/capture helpers and executed the tests/browser. Reviewer was read-only, did not implement code, run builds, use GPU or contact the user. This is an independent cross-model source review, followed by retained actual Web evidence review described below. Earlier source-only stage findings are preserved here as history.

Frozen reviewed preview identities:

| File | SHA256 |
|---|---|
| src/lib.rs |7720a9957d4d58db325a038cb685629b4c03501ca48a94441af47d64c9e9232b|
| src/binding.rs |54648029c2ac1bbf4ab69b29dfbe63f43c05bf0cfbf93482e7dbdf4699113072|
| src/bin/studio.rs |7d50c79355b8cc252e1b54bd1cfb13064af9cdef0fc24cb968e8f77230f1ecfa|
| index.html |c9a15443f11de3eb4435690e609475ec588411bbc20f54976bfdeaf9da28505e|

The first pass found two material diagnostic issues: a rejected Wasm command could revert to the previous cached green result on the next controller tick; ongoing playback could leave an earlier sample's proof presented as current. The implementer fixed both, and the reviewer inspected the frozen fixes: persistent rejection clears pending/queue/frame, and changed transport clears proof with an explicit stale state. Actual Web failure/recovery verification was still required at that source-only stage.

After the first source pass, actual compilation rejected private EditorState generation access(E0616) and a missing mutable mesh binding(E0596). The implementer fixed both. A targeted independent re-review verified the new identity basis: reject pending_open/open_error/unready/runtime errors, match current public Work hash and actual entity/asset-handle generations, and read authoritative numeric generations only from the successful before/after snapshots. It rechecked identical and failed reopen handling in source; actual runtime testing was still pending at that source-only stage. The prior source pass is superseded. The corrected final source pass found no remaining concrete P1/P2 findings within this bounded scope. It checked current character/template/Cpu(0) fitted binding; full duplicate-order source IDs, source/display triangles and rest correspondence; verbatim already-flipped UVs; decoded sRGB image identity; white diffuse tint with other material properties preserved; actual plain UV/material restoration versus disposal of an old despawned binding; refit/document generation handling; and exact asset preparation/PNG bounds/CC0 closure.

Root build helpers include the copied Work fixture and reused numerical checker inputs in the frozen source closure. The sink proves only envelope consistency. The18-case checker explicitly uses three diagonal torso/jaw recipes, compares full actual/source UV arrays and compact/full reports, and feeds unchanged actual snapshots to the existing independently sourced numerical checker. No formal native/pixel/cloth-quality/performance result follows from this source review.

## Final retained Web evidence review

The reviewer checked all206 current source identities and41 Web artifact hashes against R2; all27 retained actual records against receipt/request/sample/generation identities; the18 declared numerical case bindings; and all nine actual browser screenshots. The reviewer inspected numerical results but did not rerun the checker.

Four full toggle snapshots are identical, and plain restoration returns original material/no UV/no texture. Skin captures contain22,077 actual UV entries matching fitted-source arrays, including2,262 source vertices with seams. Identical Work reopens use generations2/3 with distinct bindings; failed-Open recovery uses generation4. Screenshots show real texture and poses, persistent rejected-command error, actual HTTP404 Open failure and recovery.

The reviewer recommended accepting this **isolated Web first slice**, with no remaining P1/P2 findings. This supports the same-character skin/UV path only. Shirt/underarm/shoulder defects remain visible. Cloth quality stays HOLD; face/neck close-up quality, eyes/hair fitting, saved appearance identity, performance, native GUI and production admission remain unverified.

One nonblocking evidence wording correction was requested and applied before publication: `live_start` is a compact report in `web-observations.json` and a CUA observation, not a retained full capture. Only `live_pause.json` is the full retained playback record. See `evidence/web-events.json`.

VERIFIED — Independent frozen source and retained actual Web evidence review; material findings fixed and reviewed; no remaining P1/P2 findings in the isolated Web scope.

NOT-RUN — Reviewer-executed build/checker, native visible launch and broader appearance-quality/admission decision. Root execution evidence is recorded separately in RESULTS.md.

## Later native visual subset

The same independent Astra/high reviewer inspected all six actual native images and rehashed206 source identities, the exact compiled/copied native binary, image receipts and unchanged disk Work. No newP1/P2 was found for the explicitly limited native visual archive. See [native-independent-review.md](evidence/native-independent-review.md). No native report/frame export, exact native UV/material/geometry diagnosis, failure recovery, dedicated experiment panel, persistence, performance or production admission is credited.

Before publication, root applied the nonblocking wording cleanup: visible not-saved labels explicitly refer to Web, and issue78/PR81 blocked/draft wording is marked as historical starting context. Compiled inputs were unchanged.

PARTIAL — Actual native visual subset independently reviewed; full native appearance functionality and production admission remain open.
