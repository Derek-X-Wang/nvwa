# Headless tab raster experiment — actual result, 2026-10-13

VERIFIED — one actual hardware GPU run produced three offscreen PNGs. The
unchanged independent literal checker returned expected 0/0/1: normal Shape and
normal Profile passed; the paint-only Profile mutant failed while Profile
selection stayed held. Both normal ROIs matched all 108 sampled pixels exactly.
Independent image inspection confirmed rendered tabs. GPU and Cargo leases were
returned to root, with no active owned processes. No native window, Cua/browser
surface or server was used.

## Actual scoped pixel result

Root approved all 36 frozen inputs plus the binary, accepted lifecycle review,
confirmed competing compilers absent, and granted exactly one exclusive GPU
run. The unchanged run_owned.py launched the frozen binary via owned Popen.
It completed naturally in 7.300 seconds, exit 0, no guard error/TERM/KILL.
Actual case markers report Metal, Apple M2 Pro, IntegratedGpu, Image render
target and native_window_count0. Fixed geometry was 1280 × 720/scale1, Dark theme,
raw egui time1, no pointer/down-state by runtime assertions. The sole warning
says Metal bindless textures are unsupported and bevy_egui disabled that mode;
render/readback still completed. No palette, ROI, tolerance or source was
adjusted, and no additional renderer attempt was made.

| Actual PNG | Selected state | Checker reference | Exit | ROI errors | Bytes |
| --- | --- | --- | ---: | --- | ---: |
| normal-shape | Shape | normal-shape | 0 | 0 / 0 | 16832 |
| normal-profile | Profile | normal-profile | 0 | 0 / 0 | 16798 |
| mutant-profile | Profile | normal-profile | 1 | 0 / 182 | 16752 |

Normal and mutant Profile have the same selected state. The deliberate input
difference is active fill RGB(17,61,113)→RGB(199,13,151), affecting the production
paint closure. Inactive fill, geometry, theme, time and pointer remain fixed.
The reference checker was the pre-existing unchanged experiment31 file,
SHA256`6156f9b5f6d95ac98728eeb8ff3489bb750f741968f9fe88b3f7342b18559753`.
Its literal ROIs/colors were not derived from state, painting instructions or
output. The actual decoded mutant fails only the Profile active-fill ROI;
the inactive Shape ROI remains exact. This proves the scoped paint-only
regression can be detected beyond earlier CPU paint-instruction evidence.

All three actual PNGs are noninterlaced RGB8, 1280 × 720. The unchanged parser
validated PNG signature, size bound, IHDR, chunk lengths/CRC, IEND/no trailing
bytes, zlib byte count and scanline filters before reference comparison.
PNG SHA256s in case order:

- `6a0e50e546c5302ee7324ecba9f1cbf4bd1b9b9918ea13945053fb98eee2aa53`
- `9665af11a09b29b0e2a7fd1692dff278f870de17020611e49f416d91465b56e8`
- `10df236409468db72db60621f6a666f6979d5ed7e4683845168361e4d521b8ef`

Independent file-image inspection showed blue Shape/red Profile, then red
Shape/blue Profile, then red Shape/magenta Profile, each within the same full
beige panel/separator. Bevy's unchanged Image-target screenshot helper performs
the actual GPU readback and standard RGB8 save. No software raster, fabricated
PNG, custom recoloring or expectation adjustment was used.

Owned target PID58498 and guard PID58468 are confirmed absent by kernel ESRCH and
bounded ps no-match/no-stderr. The Popen parent reaped target exit 0. Actual
process/identity/log/checker/image/cleanup receipts are under private
`.work/m11-startup/headless32/run-1/`, curated by RUNTIME-RESULT.json. All36 frozen
inputs/binary and old30/31 frozen inputs rehashed successfully after the run.
Exact-byte copies of the three PNGs and eight log/checker/process receipts are
also retained in `evidence/run-1/`, with CURATION-MANIFEST.json source/destination
hash equality. This curation performs no rendering or image transformation.

This is a one-host/one-Metal-adapter/two-interior-ROI experiment. It does not
establish full tab geometry/text/focus behavior, native-window pixels, character
or full-application acceptance, first physical presentation, GPU performance
or memory, IME/browser coverage or permanent CI adoption. Native availability
was not queried here; explicit lock state at this callback is unknown. Old
native failure and experiment31 window-pixel NOT-RUN evidence stays unchanged.

## Build and lifecycle provenance

Baseline045d8ab unchanged production draw_tabs is 1393 bytes and exactly equal
to the current root candidate method, SHA256
`8f68b6617dbbf8bba64c389c320ea48e62dbf33c60f9e7db1e34c7ecf1abad5b`.
Package identities/checksums 524 and all 521 external feature sets match root.
Own lock/root lock/old30/31 frozen inputs rehashed successfully. No literal
checker, expected palette, ROI, tolerance or Rust painter/source adjustment
was made after the initial source freeze.

Two authorized offline/locked/release/jobs1 build attempts used the shared
target under exclusive Cargo ownership. Attempt1 passed naturally in 431.58
seconds, no error/abort, initial 52.46 GiB free. Its copied 15-minute compile guard
was later found to inherit an I/O exception cleanup gap. Root's actual CPU red
control showed the same post-Popen storage exception could abandon a dummy;
root subsequently reaped it. The live guard was preserved until attempt1 ended,
with exact source/proposal/manifest snapshots and inherited-limit note retained.

Only new32 compile guard was repaired. Mandatory finally now covers every
post-Popen operation, catches I/O/KeyboardInterrupt/cancel paths, and attempts
bounded owned-group TERM/KILL with kernel birth/session/binary identity checks
and direct-child waitpid proof. Unknown cannot become successful cleanup or
signal authority. Final receipt-write errors remain failures and cannot bypass
cleanup. Ten real CPU controls passed, including the matching fault-red family,
normal/timeout/cancel/TERM-to-KILL and explicit unknown/no-false-success checks.
They started no Cargo or GPU and left no owned processes. Initial guard/red
receipt and the first green before binary-hash strengthening remain archived.

The required second cached Cargo build under fixed guard passed in 2.01 seconds,
initial 53.27 GiB free, exit 0, no abort/errors, cleanup exit_verified. Both actual
Cargo groups 32139 and 52262 are confirmed absent via kernel killpg0/ESRCH; bounded
ps returned no-match/no-stderr. Original exp30 guard/source bytes remain intact.

Frozen binary:
`.work/m11-startup/headless32/frozen/nvwa-tab-pixels-headless-experiment`,
89862992 bytes, SHA256
`c4934df0bf0fc6fb8ded00e5e9d2248b26de2cb64906dea41cd3e7cee6ef1bff`.
It matches the actual second shared-target build. Rust source SHA256 is
`28b71bf651092a672c97e14a845d12eced950afd210065b3a896579c6a469159`.
Fixed compile guard SHA256 is
`f349ec4ecbb75e6114fef3cb3ad13ac6e8ceaeaf0abd6a162bb1129ccf8bfe8f`.
The 10-control receipt SHA256 is
`0309487ca7660975cf3b9f180ccf79caba034231bbb62dde8c49ae25f6fb5ae5`.
BUILD-RESULT.json and BUILD-DELIVERY-MANIFEST.json retain all exact hashes,
build receipts, feature parity and post-build input/cleanup checks.

The one root-granted run has now completed. Any new renderer run requires new
authorization and an empty evidence directory; this experiment did not retry.
The native Window and full-application limitations above remain unchanged.
