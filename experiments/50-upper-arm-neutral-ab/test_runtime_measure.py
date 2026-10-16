#!/usr/bin/env python3
"""Exercise actual measure() with malformed native/Web retained-capture copies."""
import copy
import json
from pathlib import Path
import sys
import unittest
import candidate as c
import runtime_evidence as r

class CapturePairControls(unittest.TestCase):
    def test_incomplete_or_wrong_capture_never_emits_pass(self):
        original=r.R
        directory=c.ROOT/'.work/m2-neutral-ab/runtime-measure-controls'/('optimized' if sys.flags.optimize else 'normal')
        directory.mkdir(parents=True,exist_ok=True)
        records=[]
        try:
            for variant in ['baseline','candidate']:
                for platform in ['native','web']:
                    for mutation in ['empty','truncated','failed','wrong_platform']:
                        with self.subTest(variant=variant,platform=platform,mutation=mutation):
                            folder=directory/(variant+'-'+platform+'-'+mutation);folder.mkdir(exist_ok=True)
                            for v in ['baseline','candidate']:
                                for p in ['native','web']:
                                    value=json.loads((original/(p+'-'+v+'.json')).read_text())
                                    if (v,p)==(variant,platform):
                                        if mutation=='empty':value['samples']=[]
                                        elif mutation=='truncated':value['samples']=value['samples'][:-1]
                                        elif mutation=='failed':value['status']='failed';value['error']='authored negative control'
                                        else:value['platform']='web' if platform=='native' else 'native'
                                    (folder/(p+'-'+v+'.json')).write_text(json.dumps(value)+'\n')
                            r.R=folder
                            with self.assertRaisesRegex(ValueError,'complete fixed-seven') as rejected:
                                r.measure()
                            self.assertFalse((folder/'runtime-directions.json').exists())
                            records.append({'variant':variant,'platform':platform,'mutation':mutation,'status':'REJECTED','error':str(rejected.exception),'pass_output_written':False})
            (directory/'controls.json').write_text(json.dumps({'status':'PASS','cases':records},indent=2)+'\n')
        finally:r.R=original
    def test_restored_pair_still_passes(self):
        original=r.R
        folder=c.ROOT/'.work/m2-neutral-ab/runtime-measure-controls'/('restored-optimized' if sys.flags.optimize else 'restored-normal');folder.mkdir(parents=True,exist_ok=True)
        try:
            for variant in ['baseline','candidate']:
                for platform in ['native','web']:(folder/(platform+'-'+variant+'.json')).write_bytes((original/(platform+'-'+variant+'.json')).read_bytes())
            r.R=folder;result=r.measure();self.assertEqual(result['status'],'PASS')
            for variant in ['baseline','candidate']:self.assertEqual(len(result['variants'][variant]['samples']),7)
        finally:r.R=original
if __name__=='__main__':unittest.main(verbosity=2)
