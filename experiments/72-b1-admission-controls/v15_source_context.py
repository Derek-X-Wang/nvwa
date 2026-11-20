"""Exact V15 experimental live-source candidate; no runtime or release claims."""
from pathlib import Path
import hashlib
import json
import stat

NAME = 'input-context-v15-experimental-v1.json'
SHA = '9a4e0a4d7c1b51b689c39b8b3d15ffffa6d26177060d8f74cde30ea3198591ed'
ID = 'nvwa-v15-experimental-source-context-v1'
PREDECESSOR = '23bcfbc4f01ade8c4ef5bb05e4ba1e300e13dcc6'
PREFIX = 'assets/characters/mpfb-b1-v15'
EXP = Path(__file__).resolve().parent
MARKERS = (PREFIX, 'crates/nvwa-cli/tests/belly_shape.rs', 'crates/nvwa-core/tests/belly_shape.rs',
           'docs/experiments/b1-belly-shape-v15.md', 'scripts/build-belly-shape-v15.py')


def present(root):
    for name in MARKERS:
        path = root / name
        if path.exists() or path.is_symlink():
            return True
    return False



def need(ok, detail):
    if not ok:
        raise ValueError('V15 exact source: ' + detail)


def file(root, name):
    path = root
    for bit in name.split('/'):
        need(bit not in ('', '.', '..'), 'unsafe relative path: ' + name)
        path = path / bit
        need(not path.is_symlink(), 'symlink: ' + name)
    need(path.is_file(), 'missing/nonregular: ' + name)
    return path


def pin(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}



def records():
    raw = file(EXP, NAME).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == SHA, 'manifest identity')
    value = json.loads(raw)
    need(set(value) == {'format', 'predecessor_commit', 'before', 'after'}
         and value['format'] == ID and value['predecessor_commit'] == PREDECESSOR
         and value['before'].keys() == value['after'].keys(), 'manifest schema or predecessor')
    need(all(i != value['after'][p] for p, i in value['before'].items()), 'inert delta')
    return value


def inventory(root, prefix):
    directory = root / prefix
    paths = [directory, *directory.parents]
    need(all(not p.is_symlink() for p in paths) and directory.is_dir(), 'bad asset root ' + prefix)
    result = set()
    for node in directory.rglob('*'):
        mode = node.lstat().st_mode
        need(stat.S_ISREG(mode) or stat.S_ISDIR(mode), 'nonregular asset tree node ' + str(node))
        if stat.S_ISREG(mode):
            result.add(node.relative_to(root).as_posix())
    return result


def verify(root, predecessor):
    value = records()
    before, after = value['before'], value['after']
    for name in set(predecessor) & before.keys():
        need(predecessor[name] == before[name], 'wrong predecessor pin ' + name)
    expected = predecessor | after
    for name, item in expected.items():
        need(pin(file(root, name)) == item, 'source bytes mismatch: ' + name)
    for version in range(9, 16):
        prefix = f'assets/characters/mpfb-b1-v{version}'
        actual = inventory(root, prefix)
        need(actual == {p for p in expected if p.startswith(prefix + '/')}, 'asset inventory mismatch: ' + prefix)
    return ID, expected
