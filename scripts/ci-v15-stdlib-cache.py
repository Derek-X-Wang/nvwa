#!/usr/bin/env python3
"""Build a replay-private checked-hash cache of the installed CPython stdlib."""
import hashlib
import importlib.util
import json
import marshal
import os
from pathlib import Path
import stat
import struct
import sys
import sysconfig
import time


EXCLUDED = {
    "__pycache__", "dist-packages", "ensurepip", "idlelib", "site-packages",
    "lib-dynload", "test", "testdata", "tests", "tkinter", "turtledemo", "venv",
}
MODES = (0, 1)
CHECKED_HASH_FLAGS = struct.pack("<I", 3)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def validate_ancestry(path, *, scratch=False, owners=None):
    """Require canonical directories, permitting protected sticky temp parents."""
    need(path.is_absolute() and path.resolve(strict=True) == path,
         "noncanonical directory: " + str(path))
    for directory in (path, *path.parents):
        info = directory.lstat()
        # The filesystem root is the mount anchor, not an installation entry.
        if owners is not None and directory != directory.parent:
            need(info.st_uid in owners, "untrusted directory owner: " + str(directory))
        writable = info.st_mode & 0o022
        protected_temp = scratch and info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
        need(stat.S_ISDIR(info.st_mode) and (not writable or protected_temp),
             "unsafe directory ancestry: " + str(directory))


def installed_runtime():
    need(sys.implementation.name == "cpython" and sys.platform == "linux"
         and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode
         and sys.flags.optimize == 0 and sys.pycache_prefix is None,
         "stdlib prewarm needs isolated, no-site, no-bytecode CPython on Linux")
    base = Path(sys.base_prefix)
    stdlib = Path(sysconfig.get_path("stdlib"))
    dynamic = stdlib / "lib-dynload"
    executable = Path(sys.executable).resolve(strict=True)
    need(sys.prefix == sys.base_prefix == sys.base_exec_prefix and
         stdlib.is_relative_to(base) and executable.is_relative_to(base),
         "unexpected interpreter installation")
    owner = stdlib.lstat().st_uid
    for path in (base, stdlib, dynamic, executable.parent):
        validate_ancestry(path, owners={0, owner})
    info = executable.lstat()
    need(owner != os.geteuid() and info.st_uid == owner and stat.S_ISREG(info.st_mode)
         and not info.st_mode & 0o022,
         "stdlib and interpreter must come from the same protected installation")
    zip_path = stdlib.parent / ("python" + str(sys.version_info.major) + str(sys.version_info.minor) + ".zip")
    need(not zip_path.exists() and not zip_path.is_symlink()
         and sys.path == list(map(str, (zip_path, stdlib, dynamic))),
         "unexpected isolated interpreter import search path")
    return executable, stdlib, owner


def allowed_component(name):
    return name not in EXCLUDED and not name.startswith(".")


def source_files(stdlib, owner):
    def onerror(error):
        raise error

    for directory, dirs, files in os.walk(stdlib, onerror=onerror, followlinks=False):
        parent = Path(directory)
        for name in tuple(dirs):
            if not allowed_component(name) or (parent == stdlib and name not in sys.stdlib_module_names):
                dirs.remove(name)
                continue
            node = parent / name
            info = node.lstat()
            need(stat.S_ISDIR(info.st_mode) and info.st_uid == owner and not info.st_mode & 0o022,
                 "untrusted stdlib directory: " + str(node))
        for name in sorted(files):
            path = parent / name
            if path.suffix != ".py" or not allowed_component(name) or (
                    parent == stdlib and path.stem not in sys.stdlib_module_names):
                continue
            yield path
        dirs.sort()


def read_source(path, owner):
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_uid == owner and not info.st_mode & 0o022,
         "untrusted stdlib source: " + str(path))
    return path.read_bytes()


def cache_payload(raw, path, mode):
    # CPython checked-hash pyc: current interpreter's magic, PEP 552 flags,
    # source hash, and the result of this interpreter's genuine compiler.
    code = compile(raw, str(path), "exec", dont_inherit=True, optimize=mode)
    return (importlib.util.MAGIC_NUMBER + CHECKED_HASH_FLAGS + importlib.util.source_hash(raw)
            + marshal.dumps(code))


def sha(raw):
    return hashlib.sha256(raw).digest()


def validate_cache(prefix, expected, sources, owner):
    uid = os.geteuid()
    validate_ancestry(prefix, scratch=True, owners={0, uid})
    info = prefix.lstat()
    need(info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700,
         "stdlib cache root must stay private")
    found = set()
    directories = {parent for file in expected
                   for parent in file.parents if parent.is_relative_to(prefix)}
    for directory, dirs, files in os.walk(prefix, followlinks=False):
        current = Path(directory)
        for name in dirs:
            path = current / name
            info = path.lstat()
            need(path in directories and stat.S_ISDIR(info.st_mode) and info.st_uid == uid
                 and stat.S_IMODE(info.st_mode) == 0o700, "unexpected cache directory: " + str(path))
        for name in files:
            path = current / name
            info = path.lstat()
            need(path in expected and stat.S_ISREG(info.st_mode) and info.st_uid == uid
                 and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600,
                 "unexpected cache entry: " + str(path))
            # A checked source hash alone is not a signature for the executable
            # payload. Match the complete bytes produced by our fresh compile.
            need(sha(path.read_bytes()) == expected[path], "changed compiled cache payload: " + str(path))
            found.add(path)
    need(found == expected.keys(), "incomplete stdlib cache")
    for path, digest in sources.items():
        need(sha(read_source(path, owner)) == digest, "stdlib source changed while prewarming: " + str(path))


def prewarm(scratch):
    start = time.monotonic()
    executable, stdlib, owner = installed_runtime()
    validate_ancestry(scratch, scratch=True, owners={0, os.geteuid()})
    info = scratch.lstat()
    need(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700,
         "replay scratch must be private")
    prefix = scratch / "stdlib-bytecode-cache"
    prefix.mkdir(mode=0o700)
    sources = {}
    expected = {}
    sys.pycache_prefix = str(prefix)
    try:
        for path in source_files(stdlib, owner):
            raw = read_source(path, owner)
            sources[path] = sha(raw)
            for mode in MODES:
                destination = Path(importlib.util.cache_from_source(str(path), optimization=str(mode or "")))
                need(destination.is_relative_to(prefix) and destination not in expected,
                     "unsafe or repeated CPython cache path")
                data = cache_payload(raw, path, mode)
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with destination.open("xb") as output:
                    output.write(data)
                expected[destination] = sha(data)
    finally:
        sys.pycache_prefix = None
    need(stdlib / "pathlib.py" in sources or stdlib / "pathlib" / "__init__.py" in sources,
         "found no usable stdlib source inventory")
    validate_cache(prefix, expected, sources, owner)
    return {"interpreter": str(executable), "python": sys.version.split()[0], "source_files": len(sources),
            "checked_hash_files": len(expected), "modes": list(MODES),
            "elapsed_seconds": round(time.monotonic() - start, 3)}


if __name__ == "__main__":
    try:
        need(len(sys.argv) == 2, "expected the replay's private scratch directory")
        os.umask(0o077)
        print(json.dumps(prewarm(Path(sys.argv[1])), sort_keys=True), flush=True)
    except (OSError, ValueError, SyntaxError) as error:
        print("stdlib prewarm rejected: " + str(error), file=sys.stderr)
        sys.exit(1)
