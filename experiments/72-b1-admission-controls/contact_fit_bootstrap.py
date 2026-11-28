"""Authenticate the executable contact-fit helper before loading candidate code."""
import hashlib
import json
import re

FIT_HELPER_TEMPLATE_SHA = '8edc51c8aee1773a2dc1d74c4c585bac3346e18b2a58f0bf901f25ceae3af37e'


def fit_bytes(exp):
    helper = exp / 'contact_fit_source_context.py'
    manifest = exp / 'input-context-contact-fit-v1.json'
    for path in (helper, manifest):
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing/nonregular contact-fit authority: ' + path.name)
    raw, policy = helper.read_bytes(), manifest.read_bytes()
    field = rb"(?m)^SHA = '([0-9a-f]{64})'$"
    if re.findall(field, raw) != [hashlib.sha256(policy).hexdigest().encode('ascii')]:
        raise ValueError('contact-fit helper manifest binding')
    canonical = re.sub(field, b"SHA = '" + b'0' * 64 + b"'", raw)
    digest = hashlib.sha256(canonical).hexdigest()
    if digest != FIT_HELPER_TEMPLATE_SHA or json.loads(policy).get('helper_template') != {
            'bytes': len(raw), 'template_sha256': digest}:
        raise ValueError('contact-fit helper template identity')
    return raw
