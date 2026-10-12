# Independent review of bounded scale and IME diagnostics

Reviewer: native subagent `bounded_scale_ime_review`, GPT-6 Astra, read-only.
Implementation/preparation workers: `scale3_fixed_css` and `ime32_provenance`.
Root alone operated Chrome/native UI and assembled the raw evidence. The
reviewer ran CPU controls and inspected the packet and saved screenshots; it
did not run the UI, physical input, GPU tests or production builds.

## Findings, repairs and rereview

- P2: an impossible rolling-buffer inventory could pass. The checker now
  requires retained=min(recorded,1200) and dropped=max(recorded-1200,0).
  The genuine full1200-row tail passes and the fabricated two-row truncation
  fails. Red-before and green-after logs are retained;26 scale tests pass.
- P2: contradictory IME hook/module/case timestamps could pass. The checker
  now requires finite nonnegative, ordered timestamps and valid checkpoint
  types. The worker reported35 failing pre-fix assertions/subtests in truncated
  tool output; a complete original red log was not saved. The independently
  reproduced20-test green output is archived. Three preparation mutation
  controls also pass.
- Root's initial actual scale captures were rejected for window-blur. The
  observer's capture-phase callbacks had included descendant focus/blur.
  The two callbacks now require `event.target === window`; an actual-collector
  semantic control proves both descendant rejection and window-event retention.
  V1 raw/package bytes remain rejected and unchanged. V2 uses new package
  hashes, one preconditioning click and a separately evaluated settled click.
  No production focus logic or existing experiment20 check was weakened.
- P2 in publication: preparation mutation tests require the accepted `dist/web`
  bundle and a private parent directory. Their command was moved out of the
  cache-free packet reproduction block, with these prerequisites stated.

Final rereview found no actionable issue in the then63 manifest entries,
31 frozen production inputs, six selected scale intervals, complete Work
snapshots, actual synthetic IME capture and18 saved screenshots. The normal
87-row and fixed321-row traces are stopped with no dropped rows. Click/Undo
results and their exact revision transitions agree with the saved Works.
The attempted tool drag has down/up endpoints and no held pointermove; it
does not prove continuous dragging.

Native exported JSON confirms readiness at2x and screenshots show the separate
click/Undo and window-enlargement checks. The reviewer did not independently
inspect the private full native log or root's shell exit attribution. No native
whole-Work exchange or display-scale transition is claimed by this packet.

The actual Chrome IME selftest proves the known local synthetic call path only.
The later physical pair is reviewed separately below. Original event710 stays
UNKNOWN. Keep #3 open: these controls neither
reproduce the original IAB emulated-DPR failure nor establish its cause.

## Actual-pair rereview

The same independent reviewer inspected both exact stopped raw exports and saved
screenshots. Plain52/Nvwa42 rows have ordered chronology, intact early hooks,
zero drops/errors, DPR2.5 and the intended focused/visible target during
composition. Both exact checker results remain PARTIAL/exit2 without contradiction
problems. The Nvwa hook precedes its module; each trace has trusted length
sequence0→1→2→4→2 followed by an untrusted length2 end with no dispatch witness.

Both saved surfaces show 女娲 once. Space follows composition end with
composing:false and insertText length1; candidate selection and placement are
NOT-RUN. Sogou identity is human-reported; version/provider internals remain
unknown. The plain capture includes roughly114 minutes of mostly idle elapsed
time. Generic page-state focus/blur lacks event targets and may include descendant
focus; do not treat every such row as a window transition.

The paired result supports only that the pattern is not specific to Nvwa in
this instrumented environment. Shared instrumentation remains a possible effect;
absence of a witness does not establish the cause. Old710 stays UNKNOWN. The
reviewer accepts ending/closing the diagnosis-only #32 with these explicit
limits and no further physical repeat. This does not imply a product fix or
completion of the separate candidate/Space checks. #3 remains open.

Final publication rereview checked78 inventory entries and byte-exact identities
of the paired archives. Cleanup was observed by root, not independently by the
reviewer. The page captured after the permission reset shows the stopped Nvwa
page rather than the permission popover; it does not prove the setting. The
restoration to Ask is explicitly root-observed live AX evidence in cleanup.json.
The screenshot is named `page-after-permission-reset.jpg` to state that limit.

PARTIAL — Bounded controls and actual pair reviewed; event origin and original
IAB/display-transition scope remain unverified.
