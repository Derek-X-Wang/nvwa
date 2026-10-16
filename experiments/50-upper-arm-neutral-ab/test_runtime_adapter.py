#!/usr/bin/env python3
"""Reject wrong variant/capture mutations through the actual runtime adapter."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import candidate as c
spec=importlib.util.spec_from_file_location('adapter50',c.HERE/'probe/compare.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class RuntimeIdentityControls(unittest.TestCase):
    def capture(self,variant):return json.loads((c.HERE/'results'/('native-'+variant+'.json')).read_text())
    def test_baseline_cannot_pass_as_candidate(self):
        with self.assertRaisesRegex(ValueError,'complete Work identity'):
            a.compare(self.capture('baseline'),'candidate')
    def test_candidate_cannot_pass_as_baseline(self):
        with self.assertRaisesRegex(ValueError,'complete Work identity'):
            a.compare(self.capture('candidate'),'baseline')
    def test_unchanged_descendant_rotation_is_checked(self):
        capture=self.capture('candidate');node=next(n for n in capture['samples'][0]['nodes'] if n['gltf_node_index']==3)
        node['rotation']=[0.,0.,0.,1.]
        with self.assertRaisesRegex(ValueError,'actual parent propagation consistency'):
            a.compare(capture,'candidate')
    def test_root_translation_is_checked(self):
        capture=self.capture('candidate');node=next(n for n in capture['samples'][0]['nodes'] if n['gltf_node_index']==17)
        node['translation'][0]+=.01
        with self.assertRaisesRegex(ValueError,'actual parent propagation consistency'):
            a.compare(capture,'candidate')
    def test_exact_key_is_checked(self):
        capture=self.capture('candidate');capture['samples'][-1]['source_key_index']=88
        with self.assertRaisesRegex(ValueError,'exact seven keys'):
            a.compare(capture,'candidate')
if __name__=='__main__':unittest.main(verbosity=2)
