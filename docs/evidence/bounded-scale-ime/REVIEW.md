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
Physical plain/Nvwa comparison and OS input-method/provider identity remain
pending. Original event710 stays UNKNOWN. Keep #3 open: these controls neither
reproduce the original IAB emulated-DPR failure nor establish its cause.

PARTIAL — Diagnostic repairs, controls and archived evidence accepted. Physical
IME comparison and original IAB/display-transition scope remain unverified.
