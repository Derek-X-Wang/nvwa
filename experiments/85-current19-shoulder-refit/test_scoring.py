"""Default-slot contract controls; no actual geometry/candidate score is performed."""
import unittest
from unittest.mock import patch
import current19 as c
import scoring as s


def result(case,before,after):
    return {'case':case,'failures':[],
            'fixed_default_ROI':{'baseline':{'body_first':before},'candidate':{'body_first':after}}}


class DefaultROIControls(unittest.TestCase):
    def score(self,before,after):
        value=result(c.ANCHOR,before,after)
        # Exercise the production current19 adapter, while labeling math as NOT-RUN.
        with patch.object(s.e,'score_case',return_value=value) as scorer:
            actual=s.score_case(c.ANCHOR,None,None,None,None,None,None,None)
            self.assertEqual(scorer.call_args.args[0],c.ANCHOR)
            return actual
    def test_default_equal_rejects(self):
        self.assertIn('no_measurable_default_ROI_benefit',self.score(20,20)['failures'])
    def test_default_worse_rejects(self):
        self.assertIn('no_measurable_default_ROI_benefit',self.score(20,21)['failures'])
    def test_default_strict_improvement(self):self.assertEqual(self.score(20,19)['failures'],[])
    def test_zero_equal_rejects(self):self.assertTrue(self.score(0,0)['failures'])
    def test_original_gate_failures_survive(self):
        value=result(c.ANCHOR,20,19);value['failures']=['new_proper_crossing:body_pairs']
        self.assertEqual(s.default_roi_gate(value)['failures'],['new_proper_crossing:body_pairs'])
    def test_legacy_slot_not_relabeled(self):
        case=c.case_name((0,c.ARM,16))
        self.assertEqual(s.default_roi_gate(result(case,20,20))['case'],case)
    def test_unknown_slot_rejects(self):
        with self.assertRaises(ValueError):s.default_roi_gate(result('original-fresh-default-anchor',20,19))
    def test_bad_count_rejects(self):
        with self.assertRaises(ValueError):self.score(True,0)


if __name__=='__main__':unittest.main()
