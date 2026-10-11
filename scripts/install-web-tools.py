"""Install the pinned official wasm-bindgen CLI into this project only."""
from pathlib import Path, PurePosixPath
import hashlib
import os
import shutil
import tarfile
import urllib.request

root = Path(__file__).resolve().parent.parent
name = 'wasm-bindgen-0.2.129-aarch64-apple-darwin.tar.gz'
archive_path = root / '.tools/downloads' / name
archive_path.parent.mkdir(parents=True, exist_ok=True)
url = 'https://github.com/wasm-bindgen/wasm-bindgen/releases/download/0.2.129/' + name
expected = '81d4a23d56b3c3eb8187658329116d50e0b228a93b343825fb71f70179051cd1'
if not archive_path.exists():
    urllib.request.urlretrieve(url, archive_path)
if hashlib.sha256(archive_path.read_bytes()).hexdigest() != expected:
    raise SystemExit('Official tool archive hash mismatch; refusing to execute it')
out = root / '.tools/wasm-bindgen'
with tarfile.open(archive_path) as archive:
    for member in archive.getmembers():
        rel = PurePosixPath(member.name)
        if rel.is_absolute() or '..' in rel.parts or not (member.isdir() or member.isfile()):
            raise SystemExit('Unsafe archive member: ' + member.name)
        target = out.joinpath(*rel.parts)
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open('wb') as destination:
                shutil.copyfileobj(source, destination)
            os.chmod(target, member.mode & 0o777)
print('Installed verified wasm-bindgen 0.2.129 for macOS arm64 in .tools/')
