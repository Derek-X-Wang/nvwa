"""Verify later saved Works and capture copies. This script does not drive UI."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path


def main():
    directory = Path(__file__).resolve().parent

    def read(path):
        return json.loads(path.read_text())

    for name, entry in read(directory / "MANIFEST.json")["files"].items():
        data = (directory / name).read_bytes()
        assert len(data) == entry["bytes"], name
        digest = hashlib.sha256(data).hexdigest()
        assert digest == entry["public_sha256"] == entry["source_sha256"], name

    web = read(directory.parent / "web-redo.nvwa.json")
    assert read(directory / "web-through-native.nvwa.json") == web
    assert read(directory / "native-reloaded.nvwa.json") == web
    modified = deepcopy(web)
    modified["revision"] = 5
    modified["character"]["parameters"]["jaw_width"] = 0.6
    assert read(directory / "native-before-reload.nvwa.json") == modified
    handback = read(directory.parent / "native-redo.nvwa.json")
    handback["revision"] = 8
    assert read(directory / "native-human-followup.nvwa.json") == handback
    assert read(directory / "native-1175-layout.nvwa.json") == handback
    assert read(directory / "native-1024-layout.nvwa.json") == handback
    print("PASS: full Work equality for native handback, Web-to-native and native reload; exact capture hashes")
    print("NOT-RUN: this script does not drive UI or prove physical input or window geometry")


if __name__ == "__main__":
    main()
