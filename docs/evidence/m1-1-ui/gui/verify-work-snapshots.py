"""Check complete saved Works from actual UI actions; does not drive the GUI."""
from copy import deepcopy
import json
from pathlib import Path


def main():
    directory = Path(__file__).resolve().parent

    def read(name):
        return json.loads((directory / (name + ".nvwa.json")).read_text())

    source = read("source")
    assert source["revision"] == 1
    for name in ("native-layout", "web-before", "web-layout"):
        assert read(name) == source, name
    for prefix, jaw in (("native", 0.73), ("web", 0.8)):
        edited = deepcopy(source)
        edited["revision"] = 2
        edited["character"]["parameters"]["jaw_width"] = jaw
        assert read(prefix + "-edited") == edited, prefix + " edit"
        undone = deepcopy(source)
        undone["revision"] = 3
        assert read(prefix + "-undo") == undone, prefix + " undo"
        redone = deepcopy(edited)
        redone["revision"] = 4
        assert read(prefix + "-redo") == redone, prefix + " redo"
    assert read("web-reloaded") == read("web-edited")
    for name in ("web-small-layout", "web-small-split-final"):
        assert read(name) == read("web-redo"), name
    for name in ("native-through-web", "web-input-layout"):
        assert read(name) == read("native-redo"), name
    print("PASS: full Work equality for layout, edit, Undo/Redo, Web reload and native-to-Web exchange")
    print("NOT-RUN: this script does not drive UI, prove physical IME or perform Web-to-native exchange")


if __name__ == "__main__":
    main()
