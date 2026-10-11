import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from artifact import ArtifactError, import_artifact, parse_job

ROOT = Path(__file__).resolve().parent


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.job = parse_job((ROOT/'job.json').read_text())
        self.manifest = json.loads((ROOT/'artifact-manifest.json').read_text())

    def check_error(self, code, function):
        with self.assertRaises(ArtifactError) as caught:
            function()
        self.assertEqual(caught.exception.code, code)

    def import_(self, manifest=None, root=ROOT):
        return import_artifact(self.job, json.dumps(manifest or self.manifest), root)

    def test_frozen_authored_wave_import(self):
        result = self.import_()
        self.assertEqual(result['state'], 'imported')
        self.assertFalse(result['ai_generated'])
        self.assertFalse(result['prompt_alignment_measured'])
        self.assertEqual(result['source_kind'], 'authored_preset')
        self.assertEqual(result['animation_name'], 'wave')
        self.assertAlmostEqual(result['duration_seconds'], 3.0416667461395264)
        self.assertEqual(result['skin_count'], 1)

    def test_model_backend_is_explicitly_unavailable_without_fallback(self):
        self.job['backend'] = 'kimodo_local'
        self.check_error('inference_unavailable', self.import_)

    def test_ai_provenance_cannot_be_assigned_to_preset(self):
        for changes in [{'ai_generated': True}, {'source_kind': 'model_generated'}, {'model_id': 'nvidia/Kimodo-SOMA-RP-v1.1'}]:
            m = dict(self.manifest, **changes)
            self.check_error('invalid_provenance', lambda: self.import_(m))

    def test_duplicate_keys_and_unknown_job_fields_rejected(self):
        self.check_error('invalid_json', lambda: parse_job((ROOT/'job.json').read_text().replace('"seed": 42', '"seed": 99, "seed": 42')))
        bad = dict(self.job, extra='unknown')
        self.check_error('invalid_schema', lambda: parse_job(json.dumps(bad)))

    def test_nonfinite_seed_and_duration_ranges(self):
        for value in [0, -1, 11, float('inf')]:
            job = dict(self.job, duration_seconds=value)
            self.assertRaises(ArtifactError, parse_job, json.dumps(job))
        job = dict(self.job, seed=True)
        self.check_error('out_of_range', lambda: parse_job(json.dumps(job)))

    def test_job_and_duration_mismatch(self):
        bad = dict(self.manifest, job_id='another-job')
        self.check_error('job_conflict', lambda: self.import_(bad))
        self.job['duration_seconds'] = 2.
        self.check_error('duration_mismatch', self.import_)

    def test_missing_file_and_unsafe_paths(self):
        bad = dict(self.manifest, artifact_path='absent.glb')
        self.check_error('missing_artifact', lambda: self.import_(bad))
        for path in ['../authored-wave.glb', '/absolute.glb', 'https://file.glb', 'x\\file.glb']:
            bad = dict(self.manifest, artifact_path=path)
            self.check_error('unsafe_path', lambda: self.import_(bad))
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            (Path(directory)/'linked.glb').symlink_to(ROOT/'authored-wave.glb')
            bad = dict(self.manifest, artifact_path='linked.glb')
            self.check_error('unsafe_path', lambda: self.import_(bad, directory))

    def test_corrupted_hash_and_invalid_glb(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory)/'authored-wave.glb'
            data = bytearray((ROOT/'authored-wave.glb').read_bytes())
            data[-1] ^= 1
            path.write_bytes(data)
            self.check_error('hash_mismatch', lambda: self.import_(root=directory))
            data[:4] = b'NOPE'
            path.write_bytes(data)
            bad = dict(self.manifest, artifact_sha256=hashlib.sha256(data).hexdigest())
            self.check_error('invalid_artifact', lambda: self.import_(bad, directory))

    def test_requested_animation_must_exist(self):
        bad = dict(self.manifest, animation_name='model-generated-dance')
        self.check_error('missing_animation', lambda: self.import_(bad))


if __name__ == '__main__':
    unittest.main(verbosity=2)
