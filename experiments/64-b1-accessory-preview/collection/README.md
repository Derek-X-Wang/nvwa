# Collect one actual native frame

This standard-library Python CLI sends one explicit command to the running experimental Studio. It does not launch an app, create a renderer, advance through cases, or take screenshots. Use only channels and output directories that you own.

Launch the built native executable with `B1_64_COMMAND_FILE`, `B1_64_REPORT_FILE` and `B1_64_FRAME_FILE` set to three distinct absolute paths. Open the actual B1 motion Work and enable **Skin + eyes + hair**. Then collect one held frame:

```sh
python3 -B collection/collect_native.py \
  --command-file /ABS/OWNED/command.json \
  --report-file /ABS/OWNED/report.json \
  --frame-file /ABS/OWNED/frame.json \
  --out /ABS/OWNED/NEW-CASE-DIRECTORY \
  --manifest /ABS/EXPERIMENT/collection/cases54.json \
  --case t0-j0-arm-s0 --timeout 45
```

Run from this experiment directory, or use absolute script paths. The output directory must be new. The manifest contains 54 combinations, with distinct native and Web request IDs. The CLI uses only the named native case. For a repeat, supply a fresh explicit request ID through `--request-json`; it never invents an ID or resends a command.

The CLI preserves the original channel bytes, independently sent command, observed/current report and frame bytes, collector receipt, and assembled `{request,report,frame}` envelope. The envelope is explicitly **collector assembly**. A successful collection requires the requested published sample, generation, revision, parameters, geometry identity and appearance mode. Missing structure, mismatches, automatic rebind, a new runtime error or timeout fail. An unchanged error that predates dispatch may wait for the new request; a persistent old error still times out. Protected manifest/binary paths cannot alias the output channels. The timeout is at most 60 seconds.

Inspect the actual rendered frame separately. The retained run collected 54 CPU frame records per platform; native screenshots cover representative held frames and live playback, rather than all 54 native frames. These arrays and receipts are not GPU readback or an independent current-world oracle.

Check a collected accessory frame with the separate source-grounded verifier:

```sh
python3 -B verification/check_capture.py --repo /ABS/REPO \
  --capture /ABS/NEW-CASE-DIRECTORY/envelope.json \
  --command /ABS/NEW-CASE-DIRECTORY/sent-command.raw \
  --receipt /ABS/NEW-CASE-DIRECTORY/report.raw \
  --output /ABS/NEW-RESULT.json
```

The verifier is for accessory mode. Baseline and skin-only records require separate restoration/invariance checks. Do not manufacture the expected command from the capture.

`python3 -B collection/test_collector.py` runs 14 artificial file-pipeline controls. They cover rejection, preservation, path protection, empty accessory representations, and old-error recovery. They do not run the application or prove rendering.
