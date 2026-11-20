"""Materialize exact #154 Git objects for isolated unchanged Python controls."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tarfile
import tempfile

BASE = "23bcfbc4f01ade8c4ef5bb05e4ba1e300e13dcc6"
TREE = "9aec0ec20ed1ebd02419238ce29cbb70723015ec"
V15 = Path("assets/characters/mpfb-b1-v15")
EXP72 = "experiments/72-b1-admission-controls"
EXP73 = "experiments/73-high-poly-eyes"
CONTEXT_MANIFEST = EXP72 + "/input-context-v15-experimental-v1.json"
NEW_CONTEXT_CONTROLS = {CONTEXT_MANIFEST, EXP72 + "/v15_source_context.py"}
EXPERIMENT_BUILD_OUTPUTS = {"target", "__pycache__", ".work"}
STDLIB_CACHE_HELPER = "scripts/ci-v15-stdlib-cache.py"
STDLIB_CACHE_HELPER_SHA256 = "d2386c0eab74eea80b0a38b32a76aee2216debc8bd559085f0ed83ee1434aeea"


class ReplayError(Exception):
    pass


def need(ok, detail):
    if not ok:
        raise ReplayError(detail)


def clean_env():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("GIT_", "PYTHON"))}
    env.update({"GIT_NO_REPLACE_OBJECTS": "1", "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
                "PYTHONDONTWRITEBYTECODE": "1", "GIT_NO_LAZY_FETCH": "1",
                "GIT_ALLOW_PROTOCOL": ""})
    return env


def git(repo, *args):
    return subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(repo), *args], env=clean_env())


def identity(repo):
    parent_tree = git(repo, "rev-parse", "--verify", BASE + "^{tree}").decode().strip()
    need(parent_tree == TREE, "wrong baseline tree")
    # Retain only Git's original literal object identity, not a replacement ref
    # or a commit inspected through a caller-controlled repository environment.
    raw = git(repo, "cat-file", "commit", BASE)
    need(hashlib.sha1(f"commit {len(raw)}\0".encode() + raw).hexdigest() == BASE
         and raw.startswith(f"tree {TREE}\n".encode()), "baseline commit corruption")


def safe_name(name):
    if (not name or "\\" in name or name.startswith("/") or "\0" in name
            or any(x in {"", ".", "..", ".git"} for x in name.split("/"))):
        raise ReplayError("unsafe archive path")
    return name


def inventory(data):
    result = {}
    for line in data.split(b"\0"):
        if not line:
            continue
        head, raw_name = line.split(b"\t", 1)
        mode, kind, object_id = head.decode("ascii").split()
        name = safe_name(raw_name.decode("utf-8"))
        need(kind == "blob" and mode in {"100644", "100755"}
             and re.fullmatch("[0-9a-f]{40}", object_id), "unexpected Git tree member")
        need(name not in result, "duplicate Git tree member")
        result[name] = (int(mode[-3:], 8), object_id)
    need(result, "empty Git inventory")
    return result


def verify_tree(files, expected):
    # Independently reconstruct the recursively listed Git tree object. This
    # rejects a manifest whose paths/modes/object IDs do not bind to TREE.
    root = {}
    for name, (mode, object_id) in files.items():
        parent = root
        parts = name.split("/")
        for folder in parts[:-1]:
            node = parent.setdefault(folder, {})
            need(isinstance(node, dict), "mixed file and directory in tree")
            parent = node
        need(parts[-1] not in parent, "duplicate tree path")
        parent[parts[-1]] = (mode, object_id)

    def oid(children):
        data = bytearray()
        order = sorted(children, key=lambda n: n.encode() + (b"/" if isinstance(children[n], dict) else b""))
        for name in order:
            member = children[name]
            if isinstance(member, dict):
                mode, member_id = b"40000", oid(member)
            else:
                executable, member_id = member
                mode = b"100755" if executable == 0o755 else b"100644"
                member_id = bytes.fromhex(member_id)
            data.extend(mode + b" " + name.encode() + b"\0" + member_id)
        return hashlib.sha1(f"tree {len(data)}\0".encode() + data).digest()

    need(oid(root).hex() == expected, "Git inventory does not match pinned tree")


def extract_verified(source, dest, files):
    seen = set()
    allowed_dirs = {str(d) for name in files for d in Path(name).parents if str(d) != "."}
    seen_dirs = set()
    out = hashlib.sha256()
    with tarfile.open(fileobj=source, mode="r|") as archive:
        need(archive.pax_headers.get("comment") == BASE, "wrong archive commit comment")
        for member in archive:
            name = safe_name(member.name)
            local = dest / name
            if member.isdir():
                need(name in allowed_dirs and name not in seen_dirs, "unexpected directory: " + name)
                seen_dirs.add(name)
                local.mkdir(parents=True, exist_ok=True)
                continue
            need(member.isfile() and member.type in {tarfile.REGTYPE, tarfile.AREGTYPE}
                 and not member.sparse and name in files and name not in seen,
                 "unexpected or nonregular file: " + name)
            mode, object_id = files[name]
            need(member.mode & 0o111 == mode & 0o111, "executable mode mismatch: " + name)
            obj = hashlib.sha1(f"blob {member.size}\0".encode())
            sha = hashlib.sha256()
            local.parent.mkdir(parents=True, exist_ok=True)
            reader = archive.extractfile(member)
            need(reader, "missing archive data: " + name)
            count = 0
            with reader, local.open("xb") as handle:
                for chunk in iter(lambda: reader.read(256 * 1024), b""):
                    count += len(chunk)
                    obj.update(chunk)
                    sha.update(chunk)
                    handle.write(chunk)
            need(count == member.size and obj.hexdigest() == object_id, "Git blob mismatch: " + name)
            local.chmod(mode)
            seen.add(name)
            out.update(f"{name}\0{mode:o}\0{sha.hexdigest()}\n".encode())
    need(seen == files.keys(), "missing tracked archive files")
    need(not (dest / V15).exists(), "V15 contamination in historical root")
    return out.hexdigest()


def materialize(repo, live, dest):
    need(dest.resolve() != live.resolve(), "historical and live paths must differ")
    need((live / V15).is_dir() and not (live / V15).is_symlink(),
         "expected a separate live V15 tree")
    identity(repo)
    # A partial clone may have a valid commit/tree while lacking file blobs.
    # Do not let git archive's implicit promisor fetch violate offline mode.
    try:
        objects = git(repo, "rev-list", "--objects", "--no-object-names",
                      "--missing=print", TREE)
    except subprocess.CalledProcessError as error:
        raise ReplayError(f"cannot read full local baseline {BASE} tree; lazy fetch disabled") from error
    need(not any(line.startswith(b"?") for line in objects.splitlines()),
         f"incomplete local baseline {BASE} object closure; lazy fetch disabled. "
         "Fetch the baseline's complete unfiltered object pack separately while online.")
    files = inventory(git(repo, "ls-tree", "-rz", TREE))
    verify_tree(files, TREE)
    need(len(files) == 10541 and all(not (name == str(V15) or
             name.startswith(str(V15) + "/")) for name in files),
         "wrong historical inventory size or V15 presence")
    process = subprocess.Popen(
        ["git", "--no-optional-locks", "-C", str(repo), "archive", "--format=tar", BASE],
        stdout=subprocess.PIPE, env=clean_env())
    try:
        project_hash = extract_verified(process.stdout, dest, files)
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.wait(timeout=30)
    need(process.returncode == 0, "Git archive failed")
    return {"historical_commit": BASE, "historical_tree": TREE, "files": len(files),
            "independently_verified_export_sha256": project_hash}


def experiment_files(root, prefix, live=False):
    result, directories = {}, set()
    directory = root / prefix
    need(not any(p.is_symlink() for p in (directory, *directory.parents))
         and directory.is_dir(), "nonregular experiment directory: " + prefix)
    for parent, dirs, files in os.walk(directory, followlinks=False):
        current = Path(parent)
        for name in tuple(dirs):
            child = current / name
            need(stat.S_ISDIR(child.lstat().st_mode),
                 "nonregular experiment directory: " + str(child.relative_to(root)))
            if live and name in EXPERIMENT_BUILD_OUTPUTS and (
                    current == directory or name == "__pycache__"):
                dirs.remove(name)
            else:
                directories.add(child.relative_to(root).as_posix())
        for name in files:
            path = current / name
            rel = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            need(stat.S_ISREG(mode), "nonregular experiment file: " + rel)
            result[rel] = (path, bool(mode & 0o111))
    return result, directories


def source_pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def protected_experiments(live, dest):
    # An actual successful V15 production-source admission precedes this check.
    # It authenticates the independently pinned extension manifest. Compare
    # unchanged experiment helpers, tests and fixture bytes that are outside
    # that product map, without freezing unrelated files elsewhere in Nvwa.
    manifest = json.loads((live / CONTEXT_MANIFEST).read_bytes())
    before, after = manifest["before"], manifest["after"]
    need(before.keys() == after.keys(), "malformed V15 replay delta")
    additions = {}
    for exp in (EXP72, EXP73):
        old, directories = experiment_files(dest, exp)
        candidate, candidate_dirs = experiment_files(live, exp, live=True)
        need(directories == candidate_dirs, "unsupported experiment directories: " +
             ", ".join(sorted(directories ^ candidate_dirs)))
        need(old.keys() <= candidate.keys(), "missing protected experiment input: " +
             ", ".join(sorted(old.keys() - candidate.keys())))
        new_controls = {name for name in NEW_CONTEXT_CONTROLS if name.startswith(exp + "/")}
        new_delta = {name for name in after if name.startswith(exp + "/") and before[name] is None}
        allowed = new_controls | new_delta
        need(allowed <= candidate.keys() - old.keys(), "missing or historical V15 control input")
        for name, (old_path, old_executable) in old.items():
            new_path, executable = candidate[name]
            need(executable == old_executable, "changed protected experiment mode: " + name)
            if name in before:
                need(before[name] == source_pin(old_path) and after[name] == source_pin(new_path),
                     "V15 experiment before/after mismatch: " + name)
            else:
                need(old_path.read_bytes() == new_path.read_bytes(),
                     "changed protected experiment input: " + name)
        for name in new_delta:
            need(after[name] == source_pin(candidate[name][0]), "changed new V15 input: " + name)
        extra = candidate.keys() - old.keys() - allowed
        for name in extra:
            expected = re.escape(exp) + r"/test_[A-Za-z0-9_]+\.py"
            need(re.fullmatch(expected, name) and not candidate[name][1],
                 "unsupported experiment input: " + name)
        additions[exp] = {Path(name).stem for name in extra}
    return additions


def current_context(live, flags, exp, bytecode):
    if exp == EXP72:
        command = [sys.executable, "-B", *flags, f"{exp}/run.py", "--check-inputs"]
        field = "checked_input_context"
    else:
        command = [sys.executable, "-B", *flags, "scripts/check-v15-live73.py"]
        field = None
    run = subprocess.run(command, cwd=live, capture_output=True,
                         env=dict(clean_env(), PYTHONPYCACHEPREFIX=str(bytecode)))
    if run.returncode:
        sys.stderr.buffer.write(run.stdout + run.stderr)
        raise ReplayError(f"live source gate failed ({exp}): {run.returncode}")
    obj = json.loads(run.stdout)
    if field:
        obj = obj[field]
    need(obj["id"] == "nvwa-v15-experimental-source-context-v1",
         f"live source gate selected wrong context ({exp})")
    print(f"Live V15 context: {exp}, {len(obj['files']) if field else obj['files']} pins", flush=True)


def planned(live_ids, old_ids, historical):
    live, old = set(live_ids), set(old_ids)
    need(isinstance(live_ids, dict) and isinstance(old_ids, dict), "invalid suite fingerprints")
    need(old <= live, "live unittest removal: " + ", ".join(sorted(old - live)))
    need(historical and historical <= old, "historical partition contains an unknown test")
    changed = sorted(item for item in historical if live_ids[item] != old_ids[item])
    need(not changed, "changed historical-only method or setup: " + ", ".join(changed))
    current = [item for item in live_ids if item not in historical]
    retained = [item for item in old_ids if item in historical]
    need(current and retained, "empty test partner")
    return current, retained


def dispatch(live, dest, exp, flags, history_ids, additions, bytecode):
    command = [sys.executable, "-B", *flags, str(live / "scripts/v15-test-partition.py"),
               Path(exp).name]
    env = dict(clean_env(), PYTHONPYCACHEPREFIX=str(bytecode))
    live_ids = json.loads(subprocess.check_output(command, cwd=live, env=env))
    old_ids = json.loads(subprocess.check_output(command, cwd=dest, env=env))
    current, retained = planned(live_ids, old_ids, set(history_ids))
    missing = additions - {name.split(".", 1)[0] for name in current}
    need(not missing, "unexecuted newly added test modules: " + ", ".join(sorted(missing)))
    for cwd, ids in ((live, current), (dest, retained)):
        label = "live" if cwd == live else "historical"
        print(f"Test context: {exp} mode={flags or 'normal'} scope={label} count={len(ids)}", flush=True)
        subprocess.run([*command, "--run-test-ids-stdin"], cwd=cwd, env=env, check=True,
                       input=json.dumps(ids).encode())


def ci_prewarm_enabled(args, environment):
    # Do not change the default local replay, standalone/offline export, or a
    # manually narrowed probe. Only the existing GitHub-hosted job opts in.
    return (not args.offline and not args.normal_only and args.cohort is None
            and environment.get("GITHUB_ACTIONS") == "true"
            and environment.get("GITHUB_JOB") == "portable-eye"
            and environment.get("RUNNER_OS") == "Linux"
            and environment.get("RUNNER_ENVIRONMENT") == "github-hosted")


def prewarm_stdlib(live, temporary):
    helper = live / STDLIB_CACHE_HELPER
    need(helper.resolve(strict=True) == helper and stat.S_ISREG(helper.lstat().st_mode),
         "stdlib prewarm helper must be an ordinary checkout file")
    source = helper.read_bytes()
    need(hashlib.sha256(source).hexdigest() == STDLIB_CACHE_HELPER_SHA256,
         "stdlib prewarm helper identity mismatch")
    # Isolate compiler imports from the checkout, user/site hooks, and inherited
    # Python knobs. Execute the same bytes we authenticated, not a second path read.
    result = subprocess.check_output(
        [sys.executable, "-I", "-S", "-B", "-c", source.decode("utf-8"), str(temporary)],
        cwd=temporary, env=clean_env(), text=True,
    )
    try:
        receipt = json.loads(result)
    except json.JSONDecodeError as error:
        raise ReplayError("invalid stdlib prewarm receipt") from error
    need(isinstance(receipt, dict) and receipt.get("modes") == [0, 1]
         and type(receipt.get("source_files")) is int and receipt["source_files"] > 0
         and receipt.get("checked_hash_files") == 2 * receipt["source_files"],
         "invalid stdlib prewarm receipt")
    prefix = temporary / "stdlib-bytecode-cache"
    need(prefix.resolve(strict=True) == prefix and stat.S_ISDIR(prefix.lstat().st_mode),
         "missing private stdlib cache")
    print("V15 CI stdlib prewarm: " + json.dumps(receipt, sort_keys=True), flush=True)
    return prefix


def replay(live, modes, historical, temporary, cohorts, *, prewarm=False):
    dest = temporary / "tree"
    dest.mkdir()
    if not prewarm:
        bytecode = temporary / "empty-bytecode-cache"
        bytecode.mkdir()
    identity = materialize(historical, live, dest)
    print(json.dumps(identity), flush=True)
    if prewarm:
        bytecode = prewarm_stdlib(live, temporary)
    file = live / "scripts/v15-historical-test-ids.json"
    parts = json.loads(file.read_bytes())
    need(set(parts) == {EXP72, EXP73}, "wrong historical partition registry")
    for exp in cohorts:
        for flags in modes:
            current_context(live, flags, exp, bytecode)
    additions = protected_experiments(live, dest)
    for exp in cohorts:
        for flags in modes:
            dispatch(live, dest, exp, flags, parts[exp], additions[exp], bytecode)


def main():
    live = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", choices=["72", "73"], help="Otherwise run both cohorts")
    parser.add_argument("--offline", action="store_true", help="Require the exact #154 object locally")
    parser.add_argument("--normal-only", action="store_true", help="Keep standalone export in normal mode")
    args = parser.parse_args()
    cohorts = [dict(zip(("72", "73"), (EXP72, EXP73)))[args.cohort]] if args.cohort else (EXP72, EXP73)
    with tempfile.TemporaryDirectory(prefix="nvwa-v15-history-") as directory:
        scratch = Path(directory).resolve()
        repo = live
        # Do not mutate a developer's checkout. A shallow CI checkout gets
        # the literal public baseline with no credentials or history walk.
        if subprocess.run(["git", "-C", str(live), "cat-file", "-e", BASE + "^{commit}"],
                          env=clean_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            need(not args.offline,
                 f"offline source tests need baseline commit {BASE}; no download was attempted. "
                 "Prepare it separately while online from the repository checkout: "
                 f"git fetch --no-tags --depth=1 --no-recurse-submodules "
                 f"https://github.com/Derek-X-Wang/nvwa.git {BASE}")
            repo = scratch / "objects"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], env=clean_env(), check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "fetch.writeCommitGraph=false",
                            "fetch", "--no-tags", "--depth=1", "--no-recurse-submodules",
                            "https://github.com/Derek-X-Wang/nvwa.git", BASE],
                           env=dict(clean_env(), GIT_ALLOW_PROTOCOL="https"),
                           check=True, timeout=120)
        modes = ([],) if args.normal_only else ([], ["-O"])
        replay(live, modes, repo, scratch, cohorts, prewarm=ci_prewarm_enabled(args, os.environ))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ReplayError, subprocess.SubprocessError) as error:
        print(f"V15 historical replay failed: {error}", file=sys.stderr)
        sys.exit(1)
