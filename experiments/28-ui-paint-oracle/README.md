# Throwaway CPU tab paint oracle

Question: can an independent CPU paint assertion detect incorrect selected-tab
paint through the existing production UI seam, while ordinary state tests stay
green? **Yes, for the two current tabs at both tested logical viewports.**

The production file is restored to its exact starting bytes. The candidate is
retained as `candidate.patch` and `editor_layout.candidate.rs` for review only.
`paint-only-mutation.patch` records the deliberately incorrect painter branch.
No candidate or mutation remains installed in product code.

With a parent-granted single Cargo writer lease, reproduce from this exact source
cohort using `reproduce.py`. It runs only named CPU tests, restores product source
in `finally`, and refuses a changed starting cohort:

```sh
python3 -B experiments/28-ui-paint-oracle/reproduce.py
```

The test calls the existing `StudioHarness.frame` → production `draw_editor_ui`
→ real `craft_ui::Tab` painter. Expected fills and inspector text come from a
literal scripted table. It makes actual Profile and Shape clicks, releases and
removes the pointer, then checks unambiguous rectangle paint instructions behind
each real label. It retains no reference screenshot and reads no selected state
as its paint expectation. Missing labels/backgrounds, duplicate backgrounds or
zero matched tests fail. The empty-output rejection is itself a named control.

Bounds: two viewports (1280×720 and1024×768), logical scale1, fixed input time1,
no animation, eight scripted frames per viewport, at most64 nearby rectangle
observations per tab (actual two), one Cargo worker,180-second compile deadline,
and60 seconds total test execution per stage after compilation.

VERIFIED — normal paint2/state1 green; swapped-style paint1 failed/state1 green;
restored candidate paint2/state1 green. Full Work/history stayed identical.
All50 protected product input hashes match baseline after cleanup. The fresh
independent reviewer also ran the complete wrapper successfully; current stage
logs reflect that replay. This used an existing target cache. Cold compilation
within the180-second experiment deadline remains NOT-RUN.

NOT-RUN — rendered pixels, raster/GPU output, native windows, physical input/IME,
Bevy character rendering, browser/Wasm execution, zoom/DPR and cross-GPU behavior.
This experiment measures egui paint instructions, not framebuffer pixels.
