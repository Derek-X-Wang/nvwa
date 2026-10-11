#!/usr/bin/env python3
"""A bounded browser navigation's product request sum; excludes Python audits."""
import argparse
import json
from pathlib import Path

PRODUCT = {'/index.html', '/nvwa_studio.js', '/nvwa_studio_bg.wasm', '/assets/fixtures/nvwa-humanoid.glb'}
WORK = '/works/m1-sequence.nvwa.json'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--log', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
rows = [json.loads(line) for line in Path(args.log).read_text().splitlines() if line]
browser = [r for r in rows if r['client_kind'] == 'browser-candidate']
product = []
seen = set()
for row in browser:
    path = '/index.html' if row['path'] == '/' else row['path']
    if path in PRODUCT or path == WORK:
        if path in seen:
            raise SystemExit('Repeated product request: isolate one browser navigation per log, or explicitly slice the log')
        seen.add(path)
        product.append(dict(row, product_path=path))
missing = PRODUCT - seen
if missing:
    raise SystemExit('Browser first-screen inventory missing: ' + ', '.join(sorted(missing)))
if any(r['status'] != 200 or r['transfer_error'] or int(r['content_length'] or -1) != r['body_bytes_written'] for r in product):
    raise SystemExit('Product request failed or body write was incomplete')
report = {
    'product_requests': product,
    'first_screen_body_bytes_written': sum(r['body_bytes_written'] for r in product if r['product_path'] in PRODUCT),
    'player_body_bytes_written': sum(r['body_bytes_written'] for r in product) if WORK in seen else None,
    'excluded_python_audit_requests': sum(r['client_kind'] == 'python-audit' for r in rows),
    'excluded_nonproduct_browser_requests': [r['request_target'] for r in browser if ('/index.html' if r['path'] == '/' else r['path']) not in PRODUCT | {WORK}],
    'boundary': 'Observed browser-UA requests and server output.write bytes; browser/TCP receipt NOT-RUN',
    'cache_state': 'no-store local run; cold-cache NOT-RUN',
}
Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps(report, indent=2))
