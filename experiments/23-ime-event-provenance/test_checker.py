"""Checker controls only; no browser/product/physical IME is executed."""
import copy
import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('checker', Path(__file__).with_name('check.py'))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

def fixture():
    rows = [{'type':'checkpoint','label':'start'}]
    for i, event_type in enumerate(('compositionstart','compositionupdate','compositionend'),1):
        meta = dict(eventId=f'e{i}',eventType=event_type,target='ime-control',trusted=False,dataLength=2,constructorName='CompositionEvent',dispatchId=f'd{i}')
        rows += [dict(type='dispatch-start',stack='Error\n at syntheticSelftest (ime-provenance.js:1)',**meta),
                 dict(type='observed-event',provenance='WITNESSED_REALM_DISPATCH',**meta),
                 dict(type='dispatch-return',dispatchId=f'd{i}',eventId=f'e{i}',result=True)]
    rows.append({'type':'checkpoint','label':'stop'})
    for i,row in enumerate(rows,1): row.update(sequence=i,timeMs=i,hookIntact=True)
    return dict(schema=1,kind='ime-event-provenance',pageKind='synthetic-selftest',synthetic=True,
        runId='fixture-id',productionModuleStartAt=0,hookInstalledAt=0,hookIntactBeforeModule=True,running=False,startedAt=0,stoppedAt=12,earlyInstallation=True,hookIntactAtExport=True,dropped=0,instrumentationErrors=0,rows=rows)

class Tests(unittest.TestCase):
    def test_valid_selftest(self): self.assertEqual(checker.check(fixture(), True)[1],0)
    def test_missing_stack_red(self):
        c=fixture(); c['rows'][1]['stack']=None; self.assertEqual(checker.check(c,True)[1],1)
    def test_wrong_event_id_red(self):
        c=fixture(); c['rows'][2]['eventId']='other'; self.assertEqual(checker.check(c,True)[1],1)
    def test_wrong_target_red(self):
        c=fixture(); c['rows'][2]['target']='nvwa_text_input'; self.assertEqual(checker.check(c,True)[1],1)
    def test_fabricated_origin_red(self):
        c=fixture(); c['rows'][2]['dispatchId']=None; self.assertEqual(checker.check(c)[1],1)
    def test_unwitnessed_untrusted_stays_unknown(self):
        c=fixture(); c['pageKind']='nvwa'; c['synthetic']=False
        c['rows']=[c['rows'][0],dict(type='observed-event',eventId='e1',eventType='compositionend',constructorName='CompositionEvent',target='nvwa_text_input',trusted=False,dataLength=2,dispatchId=None,provenance='UNKNOWN'),c['rows'][-1]]
        for i,row in enumerate(c['rows'],1):row.update(sequence=i,timeMs=i,hookIntact=True)
        result,code=checker.check(c); self.assertEqual(code,2); self.assertEqual(result['events'][0]['provenance'],'UNKNOWN')
    def test_unwitnessed_trusted_is_not_physical_proof(self):
        c=fixture(); observed=c['rows'][2]; observed['dispatchId']=None; observed['provenance']='UNKNOWN'; observed['trusted']=True
        c['pageKind']='plain-textarea';c['synthetic']=False;c['rows']=[c['rows'][0],observed,c['rows'][-1]]
        for i,row in enumerate(c['rows'],1):row.update(sequence=i,timeMs=i)
        result,code=checker.check(c); self.assertEqual(code,0); self.assertEqual(result['events'][0]['provenance'],'UNKNOWN'); self.assertIn('NOT-RUN',result['physicalAcceptance'])
    def test_omitted_active_witness_red(self):
        c=fixture(); c['rows'][2]['dispatchId']=None; c['rows'][2]['provenance']='UNKNOWN'; self.assertEqual(checker.check(c)[1],1)
    def test_selftest_not_physical(self):
        c=fixture(); c['pageKind']='nvwa'; c['synthetic']=False; self.assertEqual(checker.check(c,True)[1],1)
    def test_terminal_and_gaps(self):
        c=fixture(); c['rows'][3]['eventId']='wrong'; self.assertEqual(checker.check(c)[1],1)
        c=fixture(); c['rows'][3]['sequence']=99; self.assertEqual(checker.check(c)[1],1)
    def test_incomplete_stop_and_drops(self):
        for field,value in [('running',True),('dropped',1),('instrumentationErrors',1),('hookIntactAtExport',False),('earlyInstallation',False)]:
            c=fixture();c[field]=value;self.assertEqual(checker.check(c)[1],2)
    def test_case_start_after_stop_red(self):
        c=fixture();c.update(startedAt=100,stoppedAt=-100)
        self.assertEqual(checker.check(c)[1],1)
    def test_rows_before_case_start_red(self):
        c=fixture();c.update(startedAt=100,stoppedAt=200)
        self.assertEqual(checker.check(c)[1],1)
    def test_nvwa_module_after_rows_red(self):
        c=fixture();c.update(pageKind='nvwa',synthetic=False,hookInstalledAt=100,productionModuleStartAt=200)
        self.assertEqual(checker.check(c)[1],1)
    def test_nan_module_red(self):
        c=fixture();c.update(pageKind='nvwa',synthetic=False,productionModuleStartAt=float('nan'))
        self.assertEqual(checker.check(c)[1],1)
    def test_invalid_timestamps_red(self):
        for field in ('hookInstalledAt','productionModuleStartAt','startedAt','stoppedAt'):
            for value in (-1,float('nan'),float('inf'),float('-inf'),True,'1'):
                with self.subTest(field=field,value=value):
                    c=fixture();c.update(pageKind='nvwa',synthetic=False);c[field]=value
                    self.assertEqual(checker.check(c)[1],1)
        for value in (-1,float('nan'),float('inf'),True,'1'):
            c=fixture();c['rows'][0]['timeMs']=value
            self.assertEqual(checker.check(c)[1],1)
    def test_rows_after_case_stop_red(self):
        c=fixture();c['stoppedAt']=5
        self.assertEqual(checker.check(c)[1],1)
    def test_invalid_boundary_checkpoint_red(self):
        for position,field,value in ((0,'type','page-state'),(-1,'type','observed-event'),(0,'label','stop'),(-1,'label','start')):
            with self.subTest(position=position,field=field):
                c=fixture();c['rows'][position][field]=value
                self.assertEqual(checker.check(c)[1],1)
        c=fixture();c['rows'][5].update(type='checkpoint',label='start')
        self.assertEqual(checker.check(c)[1],1)
    def test_valid_nvwa_chronology(self):
        c=fixture();c.update(pageKind='nvwa',synthetic=False,hookInstalledAt=0,productionModuleStartAt=0.25,startedAt=0.5)
        self.assertEqual(checker.check(c)[1],0)
    def test_privacy(self):
        c=fixture();c['rows'][2]['data']='raw';self.assertEqual(checker.check(c)[1],1)

if __name__ == '__main__': unittest.main()
