# Verification status

Native10 and Web06 build and package successfully from the same final Rust
source and embedded runtime identity. Both builds are offline, one job, with
cached dependencies. Web packaging uses wasm-bindgen 0.2.129. Exact binary,
Wasm, JavaScript, HTML and source pins are in `build-status.json`.

- Eight Rust tests exercise production state import, backend defaults, atomic
  camera metadata, CPU shader-attribute removal and garment visibility.
- Five preparation tests cover real copied sample/source corruption, missing
  runtime source, stable identity and output symlink preservation, including -O.
- Two strict comparison controls run normal and -O against actual captures;
  empty/missing parts, bones and source coverage, zero vectors/gauges and a
  ten-metre mismatch fail admission. Legacy signed GPU4 values remain diagnostic.
- Final native10 actual headless source execution passes under Python -O for
  both backends. Independent f64 arithmetic checks all 24,063 render vertices;
  maximum component error is below 1.41e-7 metres.
- JSON restores exact state. Fresh-process frame variation reaches 1.79e-7
  metres, within the declared 1e-5 metre parity tolerance; this is not bitwise
  geometry restoration. All body/garment source IDs and 53 bones are validated.
- The actual command-file boundary confirms camera-only state updates are
  atomic without a skin rerun, invalid-schema imports preserve state/frame,
  and valid recovery clears the error.
- Explicit target omission exits 1 with `Explicit target missing` and null frame.
- A real omitted-target live process acknowledges and rejects valid import,
  camera and recipe/pose/backend commands after phase 255. Its first error,
  state and null frame stay unchanged; explicit stop exits 1. Production-seam
  tests also cover a retained prior frame, later fetch/file/write failures and
  the shared native import route. Nonfatal invalid imports remain recoverable.

`native-runtime.json` records final native10 CPU evidence. It explicitly does
not claim GPU vertex readback or graphical execution.

Root owns all graphical execution. Historical native06 captures show the real
body and blue garment, corrected full framing, live recipe/pose controls and
state export. The simple source-garment visibility mask greatly reduces body
poke-through; later actual native10 diagnostic poses show visible shoulder/waist
poke-through and a folded garment. Appearance and collision acceptance are not
established. Earlier actual failures exposed
missing default tone-mapping textures and CPU joint shader attributes. Both were
fixed, then graphically retried. Original red logs/screenshots are retained in
the owned work directory.

Root reports historical Web04 booted/rendered the real character and accepted
the combined positive CPU pose/camera command at phase 4 without an error.
Putting its full frame in a textarea blocked renderer/CDP; no complete frame
was captured from that tab. Original HTML SHA is recorded. Web05 replaces that
control with a frame download. Root later observed valid import clearing a fatal error while the frame stayed
null, both after explicit omission and a fetch failure. Original red artifacts
are retained under `root-web-acceptance`. Native10/Web06 freeze the first fatal
error and state/frame until reload, reject commands, and disable native controls.
The fetch failure's cause remains unknown; root separately owns that bounded
investigation and the server cache policy change. Final graphical regression
and parity remain root-owned gates, separate from this build/headless receipt.

GPU4 quality remains HOLD. The positive-influence CPU route filters aggregate
weights >0 without a four-influence cap; it is distinct from unchanged signed
transfer and MPFB's >0.001 reference policy. The visibility mask does not prove
appearance or collision quality; diagnostic poses show shoulder/waist
poke-through and a folded garment. Native clipboard integration remains incomplete. The
107 MiB debug Wasm is not performance acceptance. No production Work adoption
is claimed.

Local-only wefty capture failed before submission with `checkout changed during
capture; retry exec`; no run ID was returned. The daily-use log records it.
The authorized direct fallback uses a private viewer target directory.
