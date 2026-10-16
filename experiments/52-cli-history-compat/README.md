# Retained CLI evidence after current source advances

The experiment38 accepted run binds eight historical CLI/core/contract source
files. New rehearsal behavior changes current source, so its unchanged source
verifier correctly rejects the current checkout. This adapter gives the original
verifier an authenticated historical context while current product tests remain
separate gates.

```sh
python3 -B experiments/52-cli-history-compat/audit.py
python3 -B experiments/52-cli-history-compat/test_controls.py
```

The default wrapper runs both unchanged `38-agent-cli/verify.py` and
`verify_controls.py`. `--check audit` or `--check controls` selects either command.
All original checks remain, including two nine-step runs, nine transport probes,
two closed-stderr controls, command/output and binary-hash bindings, and all five
original rejection/restoration controls. No old source, manifest or receipt is
rewritten. The wrapper checks inputs again after both children finish.

## Assertions stay enabled

Both original scripts use Python `assert`; they are not safe to run optimized.
The adapter always starts them with normal Python, `-I -B`, and a bootstrap that
refuses `sys.flags.optimize != 0` or false `__debug__`. It removes
`PYTHONOPTIMIZE`, `PYTHONPATH` and `PYTHONSTARTUP` from the child environment.
That also keeps assertions enabled in the unchanged subprocess commands inside
`verify_controls.py`.

The wrapper and its new refusal controls can themselves run under `-O` and/or
`PYTHONOPTIMIZE=2`. This does not claim the original scripts are optimized-safe.
A dedicated test inserts an optimization tripwire into a temporary verifier
copy, then runs the unchanged original five controls under hostile optimization
environment settings. Each nested verifier must still run normal Python.

## Small fixed context and provenance

`MANIFEST.json` binds commit `50eae1979cac47c7eb53dada69f06b716436bf92`,
tree `0bb87d9dc2ff324390de6e184852a87d513017fa`, and SHA-256/Git-blob/byte
identities for 182 files. The adapter pins the manifest SHA-256 in code.

- Eight archived source blobs total 71,075 bytes. Their hashes match all eight
  entries of the unchanged accepted source manifest. Deterministic archive paths
  are `sources/<original logical path>.txt`.
- The 174 files of the retained experiment38 directory remain live, immutable
  inputs under exact baseline pins. This includes its existing historical source
  archive and both source manifests. The original controls copy that full bounded
  directory, so its exact file set is authenticated before staging.

The temporary sparse context is 329,483 bytes. It includes no full checkout,
current product source, Git metadata, binary, build output, model or network
input. Missing/extra files, untrusted paths, symlinks, archive substitutions,
changed source/receipts/manifests and failed/timed-out children reject the run.
Temporary contexts are removed on success and failure.

## Reproduction and limits

Run the original `python3 -B experiments/38-agent-cli/verify.py` on the new Stage
checkout to reproduce its expected current-source mismatch. Then run this
adapter to verify the unchanged retained evidence in its historical context.
The 18 new tests use the actual adapter entrypoint for mutations and restored
green checks, plus direct original assertion-boundary and nested-child tests.
`VERIFICATION.json` records local results and provenance checks.

Historical source/receipt verification does not rebuild a binary, establish
signed attestation or LLM authorship, or verify current CLI behavior, GUI/Web
rendering or model inference. Current product tests and hosted CI remain separate
evidence.
