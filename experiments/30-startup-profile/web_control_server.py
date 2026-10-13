#!/usr/bin/env python3
"""Single-run9203 adapter for the unchanged experiment24 no-store server."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    if not args.root.is_absolute() or not args.evidence.is_absolute():
        parser.error("root-approved absolute frozen web and evidence paths required")
    canonical = args.root / "works/canonical-work.nvwa.json"
    expected = "cacf849f0918648a1a970452d0c33f195c5ad89fd7f6d9e58669d587d0789768"
    import hashlib
    if hashlib.sha256(canonical.read_bytes()).hexdigest() != expected:
        parser.error("frozen canonical Work does not match root-assigned exact bytes")
    work = json.loads(canonical.read_text())
    if work["revision"] != 3 or len(work["timeline"]) != 3:
        parser.error("canonical Work revision/timeline mismatch")
    source = HERE.parent / "24-http-cold-startup/server.py"
    spec = importlib.util.spec_from_file_location("nvwa_http_cache_boundary", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Fixed root-assigned port; no edit to the retained experiment24 source.
    module.PORT = 9203
    experiment = module.Experiment(args.root, args.evidence, runs=1)
    experiment.manifest["adapter"] = {"path": str(Path(__file__).resolve()),
        "sha256": module.sha(Path(__file__)), "change": "fixed9203 port and one startup"}
    (args.evidence / "manifest.json").write_text(json.dumps(experiment.manifest, indent=2) + "\n")
    server = module.ThreadingHTTPServer(("127.0.0.1", 9203), module.handler_for(experiment))
    print(json.dumps({"owned_pid": __import__("os").getpid(), "port": 9203,
        "canonicalWorkSha256": expected, "canonicalWorkRevision": 3, "timelineCount": 3,
        "url": "http://127.0.0.1:9203/run/" + experiment.run_ids[0] + "/index.html?benchmark=1&work=works/canonical-work.nvwa.json"}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
