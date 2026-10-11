"""Checker sensitivity against root's actual Chrome capture and explicit mutants.

No browser events are replayed. Mutants exist only as in-memory JSON copies.
CHECKER_PATH can select the preserved pre-fix checker for mutation-red proof.
NVWA_GEOMETRY_CAPTURE selects an explicit alternate capture; the default is
the published raw packet. A missing capture fails; it never skips or falls back.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get('CHECKER_PATH', Path(__file__).with_name('check.py')))
spec = importlib.util.spec_from_file_location('checker', SOURCE)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
CAPTURE_PATH = Path(os.environ.get('NVWA_GEOMETRY_CAPTURE',
    'docs/evidence/input-scale/observed/chrome-tab-return-scale.json'))
if not CAPTURE_PATH.is_absolute():
    CAPTURE_PATH = ROOT / CAPTURE_PATH
CAPTURE = json.loads(CAPTURE_PATH.read_text())

def args(pointer=70, row=127):
    return SimpleNamespace(pointer=pointer,row=row,expected_dpr=2,
                           expected_css=[1512,806],work_rect=[257,1,222,22])

def insert(capture, kind, **data):
    """Insert a mutant after click70; keep the packet's index/time sequence valid."""
    mutant = copy.deepcopy(capture)
    row = copy.deepcopy(mutant['rows'][70])
    row.update(index=71,timeMs=row['timeMs']+1,kind=kind,**data)
    for item in mutant['rows'][71:]:
        item['index'] += 1
    mutant['rows'].insert(71,row)
    return mutant

class GeometryCaptureTests(unittest.TestCase):
    def test_actual_close_pair_and_typing_pass(self):
        result = checker.check_geometry(CAPTURE,args())
        self.assertEqual(result['pointer'],70)
        self.assertEqual(result['row'],127)

    def test_actual_stale_pair_rejected(self):
        with self.assertRaises(AssertionError):
            checker.check_geometry(CAPTURE,args(54,242))

    def test_review_exact_stale_click_dpr_mutant_rejected(self):
        mutant = copy.deepcopy(CAPTURE)
        mutant['rows'][54]['geometry']['dpr'] = 1
        mutant['rows'][54]['geometry']['canvas']['backing'] = {'width':1512,'height':806}
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args(54,242))

    def test_review_exact_intervening_pointer_mutant_rejected(self):
        mutant = copy.deepcopy(CAPTURE)
        record = copy.deepcopy(mutant['rows'][242])
        record.update(index=999,timeMs=92660,kind='pointerdown',target='nvwa',trusted=True,
                      client={'x':1500,'y':790})
        mutant['rows'].insert(-1,record)
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args(54,242))

    def test_click_time_dpr_mutant_rejected(self):
        mutant = copy.deepcopy(CAPTURE)
        geometry = mutant['rows'][70]['geometry']
        geometry['dpr'] = 1
        geometry['canvas']['backing'] = {'width':1512,'height':806}
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args())

    def test_intervening_outside_pointer_rejected(self):
        mutant = insert(CAPTURE,'pointerdown',target='outside-control',trusted=True,client={'x':1000,'y':500})
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args(row=128))

    def test_intervening_document_focus_loss_rejected(self):
        mutant = copy.deepcopy(CAPTURE)
        mutant['rows'][75]['geometry']['documentFocused'] = False
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args())

    def test_intervening_resize_rejected_even_if_final_size_restored(self):
        mutant = insert(CAPTURE,'window-resize')
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args(row=128))

    def test_intermediate_scale_change_rejected_even_if_restored(self):
        mutant = copy.deepcopy(CAPTURE)
        mutant['rows'][75]['geometry']['dpr'] = 1
        mutant['rows'][75]['geometry']['canvas']['backing'] = {'width':1512,'height':806}
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args())

    def test_other_pointer_timer_rejected(self):
        # Actual row76 is the pending timer from earlier pointer59, only60ms
        # after pointer70. It must not be treated as pointer70's settled output.
        with self.assertRaises(AssertionError):
            checker.check_geometry(CAPTURE,args(row=76))

    def test_max_age_deadline_rejected(self):
        mutant = copy.deepcopy(CAPTURE)
        for record in mutant['rows'][127:]:
            record['timeMs'] += 750
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args())

    def test_external_focus_transfer_rejected(self):
        mutant = insert(CAPTURE,'focusin',target='outside-control',trusted=True)
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args(row=128))

    def test_index_gap_rejected(self):
        mutant = copy.deepcopy(CAPTURE)
        del mutant['rows'][75]
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args())

    def test_duplicate_index_rejected(self):
        mutant = copy.deepcopy(CAPTURE)
        mutant['rows'][75]['index'] = 74
        with self.assertRaises(AssertionError):
            checker.check_geometry(mutant,args())

    def test_retained_tail_is_only_interval_proof(self):
        mutant = copy.deepcopy(CAPTURE)
        mutant['rows'] = mutant['rows'][70:]
        result = checker.check_geometry(mutant,args())
        self.assertEqual(result['inventory']['first_index'],70)
        self.assertTrue(result['inventory']['prefix_truncated'])
        self.assertEqual(result['proof_scope'],'selected_click_interval_only')

if __name__ == '__main__':
    unittest.main()
