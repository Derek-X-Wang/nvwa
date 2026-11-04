"""Independent exact source witness for the E-only product, no renderer or dependency."""
import gzip
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'assets/characters/mpfb-b1-v4'
ORIGINALS = {
    'decr': (32837, '88613903c211706f31de1868318bfb88d51bd23791a11e1a4488266a88083396', 150149, '5d1ead7e75d7a17315dee460188676fb7e3c640c172c887309f7b655ff808c52', 13209, 178),
    'incr': (3341, '72c76aeb7956fb083aaf0d5efa00b2cdfa0f328eefc01d5e28f4610719de50c3', 13844, '4b1558340919c6a1241165129a318d838bf6eb1d39559e0ca0f0aa8b5ba6ba4e', 805, 571),
}
sha = lambda b: hashlib.sha256(b).hexdigest()

class LowerFaceSourceWitness(unittest.TestCase):
    def test_exact_original_expansions_E_fixture_and_held_decrease(self):
        source = json.loads((BASE / 'provenance/chin-bones-source.json').read_bytes())
        self.assertEqual(source['source_commit'], 'd0a32e57a7f915cb2f2b95410e2117648c7bbb7e')
        self.assertEqual(source['parameter']['range'], [0, 1])
        self.assertIn('reject', source['parameter']['negative_endpoint'])
        for suffix, pin in ORIGINALS.items():
            compressed = (BASE / f'provenance/source/data/targets/chin/chin-bones-{suffix}.target.gz').read_bytes()
            self.assertEqual((len(compressed), sha(compressed)), pin[:2])
            expanded = gzip.decompress(compressed)
            self.assertEqual((len(expanded), sha(expanded)), pin[2:4])
            self.assertEqual((BASE / f'targets/chin-bones-{suffix}.target').read_bytes(), expanded)
            rows = {}
            for line in expanded.decode('ascii').splitlines():
                cells = line.split('#')[0].split()
                if not cells:
                    continue
                self.assertEqual(len(cells), 4)
                vertex = int(cells[0])
                self.assertNotIn(vertex, rows)
                self.assertTrue(0 <= vertex < 19158)
                rows[vertex] = tuple(map(float, cells[1:]))
            self.assertEqual(len(rows), pin[4])
            self.assertEqual(sum(d != (0., 0., 0.) for d in rows.values()), pin[5])
            record = next(r for r in source['files'] if r['runtime_path'] == f'targets/chin-bones-{suffix}.target')
            self.assertEqual(record['public_nonzero_weight'], suffix == 'incr')
            if suffix == 'incr':
                self.assertEqual((ROOT / 'crates/nvwa-runtime/tests/fixtures/chin/chin-bones-incr.target').read_bytes(), expanded)

    def test_exact29_payloads_preserve_old27_and_both_appearance_sets(self):
        oldroot = ROOT / 'assets/characters/mpfb-b1-v3'
        old = json.loads((oldroot / 'manifest.json').read_bytes())
        new = json.loads((BASE / 'manifest.json').read_bytes())
        self.assertEqual(len(new['files']), 29)
        self.assertEqual(sum(f['bytes'] for f in new['files']), 6194244)
        bypath = {f['path']: f for f in new['files']}
        for item in old['files']:
            self.assertEqual(bypath[item['path']], item)
            self.assertEqual((oldroot / item['path']).read_bytes(), (BASE / item['path']).read_bytes())
        for item in new['files']:
            b = (BASE / item['path']).read_bytes()
            self.assertEqual((len(b), sha(b)), (item['bytes'], item['sha256']))
        for suffix, count in [('', 13), ('-short01-v1', 14)]:
            prior = ROOT / f'assets/appearances/mpfb-b1-cc0-v3{suffix}'
            current = ROOT / f'assets/appearances/mpfb-b1-cc0-v4{suffix}'
            old = json.loads((prior / 'manifest.json').read_bytes())
            new = json.loads((current / 'manifest.json').read_bytes())
            self.assertEqual(new['schema_version'], 4)
            self.assertEqual(new['files'], old['files'])
            self.assertEqual(len(new['files']), count)
            self.assertEqual(new['base_manifest_sha256'], sha((BASE / 'manifest.json').read_bytes()))
            self.assertEqual(new['base_asset_id'], 'mpfb-hm08-game-engine-female-sportsuit01-v4')
            for name, item in new['files'].items():
                data = (current / name).read_bytes()
                self.assertEqual(data, (prior / name).read_bytes())
                self.assertEqual((len(data), sha(data)), (item['bytes'], item['sha256']))

if __name__ == '__main__':
    unittest.main()
