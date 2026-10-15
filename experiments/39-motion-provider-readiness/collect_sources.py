#!/usr/bin/env python3
"""Fetch a fixed list of public TEXT/metadata only. Never import remote code.

No model payload, Range request, authentication, install, or model execution.
Raw responses remain in the task's private .work directory by default.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

KIMODO = '58e781898b3d7e328a676a75d3e338c45dce3ad9'
CPP = '5679ff19ba0a522c0b0516e9a9d402fe1af2c027'
MODELS = {
    'kimodo': ('nvidia/Kimodo-SOMA-RP-v1.1', '6c9233af1180b8151e3c4703477104af5dce9dd5'),
    'llama': ('meta-llama/Meta-Llama-3-8B-Instruct', '8afb486c1db24fe5011ec46dfbe5b5dccdb575c2'),
    'mntp': ('McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp', '31474e395ada192e8ed1586db6be79fb3b70c9c0'),
    'supervised': ('McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised', 'baa8ebf04a1c2500e61288e7dad65e8ae42601a7'),
    'cpp-motion': ('LocalAI-io/Kimodo-SOMA-RP-v1.1-GGML', '65f8b8ab34ee7524161cc87b20ae4cb4f5d3a12d'),
    'cpp-text': ('LocalAI-io/Llama-3-Kimodo-GGML', '3e8d958803beaddb6011ac534f2be972e2710c7d'),
}


def sources():
    result = {}
    for key, repo, pin, paths in [
        ('official', 'nv-tlabs/kimodo', KIMODO, [
            'README.md', 'CHANGELOG.md', 'LICENSE', 'ATTRIBUTIONS.MD', 'pyproject.toml',
            'docs/source/getting_started/installation.md',
            'docs/source/getting_started/installation_virtual_env.md',
            'docs/source/key_concepts/skeleton.md', 'docs/source/user_guide/output_formats.md',
            'kimodo/model/load_model.py', 'kimodo/model/kimodo_model.py',
            'kimodo/model/llm2vec/llm2vec_wrapper.py', 'kimodo/skeleton/definitions.py']),
        ('cpp', 'localai-org/kimodo.cpp', CPP, [
            'README.md', 'LICENSE', 'NOTICE', 'CMakeLists.txt', '.gitmodules',
            'docs/QUANTIZATION.md', 'docs/PROFILING.md']),
    ]:
        result[key + '-commit.json'] = f'https://api.github.com/repos/{repo}/commits/{pin}'
        for path in paths:
            result[key + '-' + path.replace('/', '__')] = f'https://raw.githubusercontent.com/{repo}/{pin}/{path}'
    for key, (repo, pin) in MODELS.items():
        result[key + '-metadata.json'] = f'https://huggingface.co/api/models/{repo}/revision/{pin}?blobs=true'
    for key, paths in {
        'kimodo': ['README.md', 'LICENSE', 'config.yaml'],
        'mntp': ['adapter_config.json'], 'supervised': ['adapter_config.json'],
        'cpp-motion': ['README.md', 'MANIFEST.json'],
        'cpp-text': ['README.md', 'MANIFEST.json', 'LICENSE-META-LLAMA-3.txt'],
    }.items():
        repo, pin = MODELS[key]
        for path in paths:
            result[key + '-' + path] = f'https://huggingface.co/{repo}/raw/{pin}/{path}'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='.work/m12-motion-readiness/sources')
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    receipts = []
    for name, url in sources().items():
        row = {'file': name, 'url': url, 'retrieved_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Nvwa-readiness-text-only/1'})
            with urllib.request.urlopen(request, timeout=20) as response:
                data = response.read(2_000_001)
                if len(data) > 2_000_000:
                    raise ValueError('text response exceeds 2 MB limit')
                data.decode('utf-8')
                row.update(status=response.status, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                           response_date=response.headers.get('Date'), last_modified=response.headers.get('Last-Modified'))
            (out / name).write_bytes(data)
        except (urllib.error.URLError, ValueError, UnicodeError) as error:
            row.update(status='error', error=str(error))
        receipts.append(row)
        print(name, row['status'], row.get('bytes', row.get('error')))
    (out / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
    if any(row['status'] != 200 for row in receipts):
        raise SystemExit('At least one source unavailable; see receipts. No retry or authentication attempted.')


if __name__ == '__main__':
    main()
