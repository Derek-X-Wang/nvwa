# Repaired PR17 validation

Final repair is the shared transport widget extraction only. Studio source SHA and actual release binaries/Wasm are in [manifest](build-manifest.json). Prior M1 evidence/manifest stays frozen as the original4af6a19 snapshot; this repair checkpoint supplements it.

VERIFIED — Fresh57workspace tests passed, zero failed/ignored; [tests](tests.log). [Fmt](fmt.log), strict [native](native-clippy.log) and [Wasm](wasm-clippy.log) clippy passed. Rebuilt [native](native-release.log) and [Web](web-release.log) release artifacts exited0. [Independent two-axis review and targeted rereviews](REVIEW.md) completed.

Actual repaired WebGPU release loaded the exchanged revision6 work, restarted and paused, then dragged global seek across turn6.9s back to a held wave4.0s; Play remained available and the real raised arm was visible ([screen](web-player-paused.png)). This was the ordinary physical1280×720 preview, without viewport emulation.

Actual packaged repaired macOS Metal Player opened the same saved work and showed the real skinned/morphed actor and transport ([capture](native-smoke.png)); smoke ran3s then closed successfully with process exit0 ([log](native-smoke.log)). Command:

```sh
./dist/Nvwa.app/Contents/MacOS/Nvwa --player --work "$PWD/docs/evidence/m1/web-sequence.nvwa.json" --smoke --smoke-seconds 3 --capture "$PWD/docs/evidence/pr17-review/native-smoke.png" --timeout 45
```

Native capture was an ordinary HiDPI2560×1440 screenshot, not a new physical1280×720 performance measurement. Fresh native pointer/keyboard hand testing is issue#2 work after merge; do not infer it from smoke. All previous M0 acceptance gaps remain open. HostedCI is NOT-RUN because no workflow is configured. No paid/cloud resource, CI change, machine-wide setting change or platform expansion was used.
