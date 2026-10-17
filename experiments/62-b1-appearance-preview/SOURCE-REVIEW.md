# Independent source review — experiment62

R1, fresh native Codex reviewer `appearance62_review`, GPT-6 Astra/high. Preview and asset implementers used GPT-6.1 Sol/high in separate worker sessions; root integrated build/capture helpers. Reviewer was read-only, did not implement code, run builds, use GPU or contact the user. This is an independent cross-model review of the Sol-authored preview/packer. Runtime and pixel review remain pending.

Frozen reviewed preview identities:

| File | SHA256 |
|---|---|
| src/lib.rs |7720a9957d4d58db325a038cb685629b4c03501ca48a94441af47d64c9e9232b|
| src/binding.rs |54648029c2ac1bbf4ab69b29dfbe63f43c05bf0cfbf93482e7dbdf4699113072|
| src/bin/studio.rs |7d50c79355b8cc252e1b54bd1cfb13064af9cdef0fc24cb968e8f77230f1ecfa|
| index.html |c9a15443f11de3eb4435690e609475ec588411bbc20f54976bfdeaf9da28505e|

The first pass found two material diagnostic issues: a rejected Wasm command could revert to the previous cached green result on the next controller tick; ongoing playback could leave an earlier sample's proof presented as current. The implementer fixed both, and the reviewer inspected the frozen fixes: persistent rejection clears pending/queue/frame, and changed transport clears proof with an explicit stale state. Actual Web failure/recovery verification is still required.

After the first source pass, actual compilation rejected private EditorState generation access(E0616) and a missing mutable mesh binding(E0596). The implementer fixed both. A targeted independent re-review verified the new identity basis: reject pending_open/open_error/unready/runtime errors, match current public Work hash and actual entity/asset-handle generations, and read authoritative numeric generations only from the successful before/after snapshots. It rechecked identical and failed reopen handling in source; actual runtime testing is still pending. The prior source pass is superseded. The corrected final source pass found no remaining concrete P1/P2 findings within this bounded scope. It checked current character/template/Cpu(0) fitted binding; full duplicate-order source IDs, source/display triangles and rest correspondence; verbatim already-flipped UVs; decoded sRGB image identity; white diffuse tint with other material properties preserved; actual plain UV/material restoration versus disposal of an old despawned binding; refit/document generation handling; and exact asset preparation/PNG bounds/CC0 closure.

Root build helpers include the copied Work fixture and reused numerical checker inputs in the frozen source closure. The sink proves only envelope consistency. The18-case checker explicitly uses three diagonal torso/jaw recipes, compares full actual/source UV arrays and compact/full reports, and feeds unchanged actual snapshots to the existing independently sourced numerical checker. No formal native/pixel/cloth-quality/performance result follows from this source review.

VERIFIED — Independent frozen source review; two material findings fixed and re-reviewed; no remaining source P1/P2 found.

NOT-RUN — Reviewer-observed compilation, actual Web/native rendering, live failure/recovery and quality/admission decision.
