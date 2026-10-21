"""Actual old rejection witness and new-cohort admission controls; no new shape."""
import argparse
import copy
import gzip
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import evaluate_rest as e
# Collector's synthetic schema fixture supplies no candidate or actual geometry.
import test_collect as schema_fixture

RETAINED=Path(os.environ.get('NVWA_SHOULDER_RETAINED','/nonexistent-nvwa-actual-control'))
FRESH=RETAINED/'h80proof-v1/combined/capture.json'

class PipelineControls(unittest.TestCase):
    def test_old_actual_rejected_pair_and_disabled_predicate_red(self):
        if not FRESH.exists():self.skipTest('explicit actual old witness unavailable')
        self.assertEqual(e.old_rejection_control(FRESH,RETAINED)['pair'],[240,13661])
        with patch.object(e.kernels,'proper_cross',return_value=False):
            with self.assertRaisesRegex(ValueError,'known rejected new pair'):
                e.old_rejection_control(FRESH,RETAINED)

    def rejected_corpus(self,mutate):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            fixture=schema_fixture.CollectorControls()
            manifest,source,anchor=fixture.corpus(directory)
            mutate(directory,manifest,source)
            e.corpus.write_json(directory/'manifest.json',manifest)
            freeze={'cohort_kind':e.COHORT_KIND,'cohort_manifest_sha256':e.digest(directory/'manifest.json'),
                    'source_inventory_sha256':source['inventory_sha256']}
            with patch.object(e.corpus,'FRESH_SHA',e.digest(anchor)):
                with self.assertRaises((ValueError,OSError,KeyError,TypeError)):
                    e.authenticate_hybrid(directory,anchor,freeze)

    def test_new_cohort_missing_at_evaluator_admission_seam(self):
        self.rejected_corpus(lambda d,m,s:(d/m['cases'][0]['path']).unlink())

    def test_new_cohort_duplicate_at_evaluator_admission_seam(self):
        self.rejected_corpus(lambda d,m,s:m['cases'].__setitem__(1,copy.deepcopy(m['cases'][0])))

    def test_new_cohort_tampered_at_evaluator_admission_seam(self):
        self.rejected_corpus(lambda d,m,s:(d/m['cases'][0]['path']).write_bytes(b'tampered'))

    def test_new_cohort_wrong_source_at_evaluator_admission_seam(self):
        self.rejected_corpus(lambda d,m,s:s.update(inventory_sha256='0'*64))

    def test_new_cohort_wrong_recipe_at_evaluator_admission_seam(self):
        def mutate(d,m,s):
            row=m['cases'][0];path=d/row['path']
            record=json.loads(gzip.decompress(path.read_bytes()))
            record['snapshot']['parameters']['torso_length']=1
            raw=json.dumps(record).encode();compressed=gzip.compress(raw,mtime=0);path.write_bytes(compressed)
            row.update(bytes=len(compressed),sha256=e.corpus.digest(compressed),raw_bytes=len(raw),raw_sha256=e.corpus.digest(raw))
        self.rejected_corpus(mutate)

    def test_new_cohort_mixed_run_at_evaluator_admission_seam(self):
        def mutate(d,m,s):
            identity=e.corpus.strict_load((d/'identity.json').read_bytes());identity['run_id']='mixed'
            e.corpus.write_json(d/'identity.json',identity)
        self.rejected_corpus(mutate)

    def test_native_manifest_cannot_enter_wasm_evaluator_route(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            e.corpus.write_json(directory/'manifest.json',{'cohort_type':'hybrid-current18-original-anchor'})
            freeze={'cohort_kind':e.WASM_COHORT_KIND}
            with patch.object(e.importlib,'import_module') as module:
                with self.assertRaisesRegex(ValueError,'kind/manifest target differs'):
                    e.authenticate_hybrid(directory,Path('not-read'),freeze)
                module.assert_not_called()

    def test_wasm_manifest_cannot_enter_native_evaluator_route(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            e.corpus.write_json(directory/'manifest.json',{'cohort_type':'hybrid-current18-wasm-original-anchor'})
            with patch.object(e.corpus,'authenticate_corpus') as native:
                with self.assertRaisesRegex(ValueError,'kind/manifest target differs'):
                    e.authenticate_hybrid(directory,Path('not-read'),{'cohort_kind':e.COHORT_KIND})
                native.assert_not_called()

    def test_unknown_target_has_no_fallback_authenticator(self):
        with self.assertRaisesRegex(ValueError,'wrong new cohort kind'):
            e.authenticate_hybrid(Path('not-read'),Path('not-read'),{'cohort_kind':'unknown-target'})

    def test_missing_wasm_module_refuses_native_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            e.corpus.write_json(directory/'manifest.json',{'cohort_type':'hybrid-current18-wasm-original-anchor'})
            missing=ModuleNotFoundError("No module named 'collect_wasm'",name='collect_wasm')
            with patch.object(e.importlib,'import_module',side_effect=missing), \
                 patch.object(e.corpus,'authenticate_corpus') as native:
                with self.assertRaisesRegex(ValueError,'authenticator unavailable; no native fallback'):
                    e.authenticate_hybrid(directory,Path('not-read'),{'cohort_kind':e.WASM_COHORT_KIND})
                native.assert_not_called()

    def test_wasm_authenticator_rejection_and_frozen_hashes_are_preserved(self):
        from types import SimpleNamespace
        for rejection in ('wrong Wasm target receipt','tampered compressed case','mixed Wasm source identity'):
            with self.subTest(rejection=rejection),tempfile.TemporaryDirectory() as directory:
                directory=Path(directory);fresh=directory/'not-read.json'
                e.corpus.write_json(directory/'manifest.json',{'cohort_type':'hybrid-current18-wasm-original-anchor'})
                freeze={'cohort_kind':e.WASM_COHORT_KIND,'cohort_manifest_sha256':'a'*64,
                        'source_inventory_sha256':'b'*64}
                from unittest.mock import Mock
                authenticator=Mock(side_effect=ValueError(rejection))
                with patch.object(e.importlib,'import_module',return_value=SimpleNamespace(authenticate_corpus=authenticator)), \
                     patch.object(e.corpus,'authenticate_corpus') as native:
                    with self.assertRaisesRegex(ValueError,rejection):
                        e.authenticate_hybrid(directory,fresh,freeze)
                    authenticator.assert_called_once_with(directory,'a'*64,'b'*64,fresh)
                    native.assert_not_called()

    def test_candidate_never_read_when_all19_baseline_preflight_fails(self):
        args=argparse.Namespace(freeze=Path('unused'),policy=Path('unused'),candidate=Path('must-not-read'),
                                corpus=Path('unused'),fresh=Path('unused'),preflight_only=False)
        with patch.object(e,'validate_freeze',return_value=({},{})), \
             patch.object(e,'authenticate_hybrid',return_value=[]), \
             patch.object(e,'baseline_preflight',side_effect=ValueError('all19 reconstruction failed')), \
             patch.object(e,'validate_source_change') as candidate_validator:
            with self.assertRaisesRegex(ValueError,'all19 reconstruction failed'):e.run(args)
            candidate_validator.assert_not_called()

if __name__=='__main__':unittest.main()
