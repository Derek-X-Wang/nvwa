# Adaptive LLM decisions

This is a contemporaneous decision log for the real agent run. It is separate
from `tests/discovery.rs`, which is a synthetic real-binary regression test.
The exact task and route attribution are in `TASK.md`.

1. Created a fresh work with the repository profile through the production
   `new` command (receipt `01-new`). Observed revision 0 and an actual saved
   file. Chose to discover that file before changing it.
2. Read production `describe-capabilities` output (receipt `02-discover`).
   Observed `character-1`, revision 0, four parameters with inclusive 0–1
   ranges, and authored `idle`, `wave`, `turn` actions. Source durations are
   3.0416667, 3.0416667, 4.0416665 seconds respectively. The task's jaw width
   0.42 and smile 0.2 fit the discovered ranges. Chose a partial parameter
   update so the other two values remain at their actual current defaults.
   Wrote `appearance.commands.json` with the discovered character ID and
   revision. The envelope shape comes from the actual discovery response.
3. Observed the appearance command succeed at revision 1 (receipt
   `03-appearance`). Chose contiguous 0–3, 3–6 and 6–9 second wall-time spans
   in task order. Used each discovered source duration divided by 3 for speed,
   rounded to f32 precision: idle/wave 1.0138889, turn 1.3472222. This fits one
   full authored action into each span. Chose `looping: false` for this bounded
   sequence. No generated motion is involved. To exercise the requested real
   recovery path, deliberately wrote a timeline request using the now-stale
   revision 0 in `stale-timeline.commands.json`. This is an intentional fault
   injection into the production CLI, not a simulated error.
4. Observed an actual exit 1, empty CLI stdout and structured stderr
   `revision_conflict`: expected 0, current 1 (receipt `04-stale-timeline`).
   Requested `inspect` of the actual appearance input before correcting it
   (receipt `05-inspect-actual`). Read revision 1, jaw width 0.42, smile 0.2,
   unchanged nose/shoulder values and the original idle timeline. Thus the
   desired appearance already exists and only the timeline needs editing.
   Wrote `corrected-timeline.commands.json` with expected revision 1 and a fresh
   command ID. Kept the intended nine-second authored sequence unchanged.
5. Observed corrected `apply` succeed at revision 2 with three timeline clips
   (receipt `06-corrected-timeline`). Ran `validate` against actual repository
   `assets` and observed `asset_checked: true`, `valid: true`, revision 2
   (receipt `07-validate-asset`). Chose `save` to make the final portable work
   explicit (receipt `08-save-final`), then inspected that exact saved file
   (receipt `09-inspect-final`). Final readback confirms nine seconds and the
   requested parameter values. The core's actual f32 serialization spells the
   idle/wave speeds `1.013889`; turn remains `1.3472222`. This is recorded output,
   not a promise of visual completion. Native/Web preview and continuing edits
   remain NOT-RUN here.
