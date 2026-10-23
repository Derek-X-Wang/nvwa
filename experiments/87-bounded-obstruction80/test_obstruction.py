#!/usr/bin/env python3
"""Analytical controls call the certificate seam consumed by the real entrypoint.

Synthetic freeze/attempt tests stop before source reconstruction; they never use
production input data and never consume a real attempt. Red mutations compile a
modified in-memory copy, never edit a saved source or historical artifact.
"""
import copy
from dataclasses import replace
from fractions import Fraction as F
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import os
import time

import obstruction as o

def fixture(z=F(9,10000)):
    return o.BoundedInput((F(1,4),F(1,4),z),
        ((F(0),F(0),F(0)),(F(1),F(0),F(0)),(F(0),F(1),F(0))),
        (F(1,2),F(1,4),F(1,4)),'m','fixture','fixture','contact-real-body-unmasked',
        F(0),'exact-serialized-binary32-source-space',tuple(o.SUPPORT),(566,),True)

def ledger_fixture():
    samples=[];rows=[];points=[]
    for i in range(27):
        ties=[{'triangle0':i}]
        if i<2:
            ties.append({'triangle0':100+i})
        own=[{'logical_sample0':i,'body_triangle0':i,'retained_slope':0}]
        if i<3:
            own.append({'logical_sample0':i,'body_triangle0':200+i,'retained_slope':0})
        rows.extend(own)
        samples.append({'logical_sample0':i,'garment_triangle0':i,'garment_sources':[0,1,2],
                        'barycentric':[0,1,0],'unmasked_real_body':ties})
        points.append({'logical_sample0':i,'garment_triangle0':i,'garment_sources':[0,1,2],
                       'barycentric':[0,1,0],
                       'unmasked_ties':[{'body_triangle0':t['triangle0']} for t in ties],
                       'original_inequalities':[{'body_triangle0':r['body_triangle0']} for r in own]})
    return {'logical_samples':samples,'rows':rows},{'counts':{'logical_points':27,'original_inequalities':30,'unmasked_ties':29},'points':points}

class CertificateTests(unittest.TestCase):
    def test_known_strict_fixture(self):
        record=o.certify(fixture())
        self.assertEqual(record['status'],'CONDITIONAL_STRICT_OBSTRUCTION')
        self.assertEqual(F(record['distance_squared_m2']),F(81,100_000_000))
        self.assertEqual(F(record['distance_upper_m']),F(9,10000))
        self.assertFalse(record['physical_domain_admitted'])
        self.assertNotIn('PASS',record.values())

    def test_missing_physical_correspondence_cannot_promote(self):
        result=o.stage_judgment(o.certify(fixture()),'UNKNOWN')
        self.assertEqual(result['status'],'REFUSE_MISSING_PREREQUISITE')
        self.assertFalse(result['physical_obstruction'])
        self.assertFalse(result['physical_domain_admitted'])
        self.assertEqual(result['conditional_arithmetic']['status'],'CONDITIONAL_STRICT_OBSTRUCTION')

    def test_threshold_equality_and_non_strict(self):
        for z in (o.FLOOR, o.FLOOR+F(1,10**14)):
            self.assertEqual(o.certify(fixture(z))['status'],'UNKNOWN_BOUND_NOT_STRICT')

    def test_upper_grid_straddle(self):
        # Exact distance is below the floor, but its reviewed upper grid reaches
        # equality. Inconclusive remains unknown; no rounding-to-reject.
        record=o.certify(fixture(o.FLOOR-F(1,10**14)))
        self.assertEqual(F(record['distance_upper_m']),o.FLOOR)
        self.assertEqual(record['status'],'UNKNOWN_BOUND_NOT_STRICT')

    def test_consumed_input_refusals(self):
        changes=[{'barycentric':(F(-1),F(1),F(1))},
                 {'barycentric':(F(0),F(0),F(0))}, {'domain':'displayed-masked'},
                 {'units':'cm'}, {'body_frame':'relative-shift'},
                 {'error_m':F(-1)}, {'error_m':F(1,1000000)},
                 {'error_basis':'trusted-old-tolerance'},
                 {'allowed_offsets':tuple(o.SUPPORT+[566])},
                 {'active_sources':(o.SUPPORT[0],)}, {'body_fixed':False},
                 {'triangle':((F(0),)*3,)*3}]
        for change in changes:
            with self.subTest(change=change),self.assertRaises(o.Refusal):
                o.certify(replace(fixture(),**change))
        self.assertEqual(o.certify(fixture())['status'],'CONDITIONAL_STRICT_OBSTRUCTION')

    def test_common_exact_rigid_transform(self):
        base=fixture()
        transform=lambda p:(-p[1]+7,p[0]-11,p[2]+3)
        changed=replace(base,point=transform(base.point),triangle=tuple(transform(p) for p in base.triangle))
        self.assertEqual(o.certify(base)['distance_squared_m2'],o.certify(changed)['distance_squared_m2'])

    def test_concrete_edge_membership(self):
        base=fixture()
        bary=o.edge_barycentric(base.point,base.triangle)
        self.assertEqual(sum(bary),1)
        self.assertTrue(all(x>=0 for x in bary))
        self.assertEqual(bary,(0,F(1,2),F(1,2)))
        self.assertEqual(o.edge_barycentric((5,0,0),base.triangle),(0,1,0))

    def test_exact_binary32_controls(self):
        for raw in ('0.1','-0.3','1.000000059604644775390625','1.000000178813934326171875','1e-40'):
            expected=F(struct.unpack('<f',struct.pack('<f',float(raw)))[0])
            self.assertEqual(o.f32(raw),expected)
        self.assertEqual(o.f32(F(1)+o.power2(-24)),1)
        self.assertEqual(o.f32(F(1)+3*o.power2(-24)),F(1)+o.power2(-22))
        self.assertEqual(o.f32(o.power2(-150)),0)
        self.assertEqual(o.f32(3*o.power2(-150)),o.power2(-148))
        for invalid in ('nan','inf',float('nan')):
            with self.assertRaises(o.Refusal):o.f32(invalid)

    def test_signed_mapping_reconstruction(self):
        # Negative helper coefficient preserved, complete ordered sum and scale.
        cage=[[F(1),F(2),F(3)],[F(3),F(6),F(9)]]
        axes={k:(0,1,F(2)) for k in 'xyz'}
        rows=[([0,1],[F(-1),F(2)],[F(1,2),F(1,2),F(1,2)])]
        self.assertEqual(o.fit_one(cage,axes,rows,0),[F(11,2),F(11),F(33,2)])

    def test_all_rows_and_ties_retained(self):
        audit,ledger=ledger_fixture()
        self.assertEqual(o.validate_ledger(audit,ledger)['unmasked_ties'],29)
        for where in ('sample','row','tie','ledgerrow','ledgertie'):
            a,l=copy.deepcopy(audit),copy.deepcopy(ledger)
            if where=='sample':a['logical_samples'].pop()
            if where=='row':a['rows'].pop()
            if where=='tie':a['logical_samples'][0]['unmasked_real_body'].pop()
            if where=='ledgerrow':l['points'][0]['original_inequalities'].pop()
            if where=='ledgertie':l['points'][0]['unmasked_ties'].pop()
            with self.subTest(where=where),self.assertRaises(o.Refusal):o.validate_ledger(a,l)
        self.assertEqual(o.validate_ledger(audit,ledger)['old_rows'],30)

    def test_production_guard_mutation_is_red(self):
        # Invalid membership control must fail if the actual consumed membership
        # predicate is removed. This compiles the production source in memory.
        source=Path(o.__file__).read_text()
        old="need(len(bary)==3 and all(x>=0 for x in bary) and sum(bary)==1, 'invalid bounded membership')"
        self.assertIn(old,source)
        altered=source.replace(old,"need(True, 'disabled membership red mutation')",1)
        module=types.ModuleType('obstruction_red_mutation')
        module.__file__=o.__file__
        sys.modules[module.__name__]=module
        try:
            exec(compile(altered,o.__file__,'exec'),module.__dict__)
            invalid=replace(fixture(),barycentric=(F(-1),F(1),F(1)))
            # Detection harness: removing the guard makes rejection expectation red.
            detected=False
            try:module.certify(invalid)
            except module.Refusal:detected=True
            self.assertFalse(detected)
            with self.assertRaises(o.Refusal):o.certify(invalid)
        finally:sys.modules.pop(module.__name__,None)

    def test_consumed_semantic_guards_mutation_red_restored(self):
        source=Path(o.__file__).read_text()
        cases=[
            ("need(value.units == 'm', 'units not admitted')",replace(fixture(),units='cm')),
            ("need(value.frame and value.frame == value.body_frame, 'relative frame mismatch')",replace(fixture(),body_frame='shifted')),
            ("need(value.domain == 'contact-real-body-unmasked', 'wrong domain')",replace(fixture(),domain='helpers')),
            ("need(value.error_basis == 'exact-serialized-binary32-source-space' and value.error_m == 0,\n         'unproved input/reconstruction error bound')",replace(fixture(),error_m=F(1))),
            ("need(list(value.allowed_offsets) == SUPPORT, 'support changed')",replace(fixture(),allowed_offsets=tuple(o.SUPPORT+[566]))),
            ("need(value.body_fixed and not set(value.active_sources).intersection(SUPPORT), 'fixed dependency failed')",replace(fixture(),body_fixed=False))]
        for index,(guard,invalid) in enumerate(cases):
            with self.subTest(index=index):
                self.assertIn(guard,source)
                altered=source.replace(guard,"need(True, 'disabled guard red mutation')",1)
                module=types.ModuleType('obstruction_semantic_red'+str(index))
                module.__file__=o.__file__;sys.modules[module.__name__]=module
                try:
                    exec(compile(altered,o.__file__,'exec'),module.__dict__)
                    # Missing guard allows invalid input, so the normal refusal
                    # expectation becomes red. Original consumed guard rejects.
                    self.assertEqual(module.certify(invalid)['status'],'CONDITIONAL_STRICT_OBSTRUCTION')
                    with self.assertRaises(o.Refusal):o.certify(invalid)
                finally:sys.modules.pop(module.__name__,None)
        self.assertEqual(o.certify(fixture())['status'],'CONDITIONAL_STRICT_OBSTRUCTION')

class FreezeTests(unittest.TestCase):
    def test_stale_hash_and_json(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'input';p.write_bytes(b'original')
            row={'path':str(p),'bytes':8,'sha256':o.digest(b'original')}
            self.assertEqual(o.read_pinned(row),b'original')
            p.write_bytes(b'mutated!')
            with self.assertRaises(o.Refusal):o.read_pinned(row)
        for value in (b'{"x":1,"x":2}',b'{"x":NaN}'):
            with self.assertRaises(o.Refusal):o.strict_load(value)

    def policy(self,out):
        return {'kind':o.KIND,'attempt_limit':1,'mode':'rejection-only','time_limit_seconds':60,
                'execution_files':o.inventory(Path(o.__file__).parent),
                'review_sha256':'a'*64,'authorization_sha256':'b'*64,
                'exclusive_output':str(out),'inputs':{}}

    def test_real_attempt_seam_synthetic_refusal_and_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'attempt'; freeze=Path(directory)/'freeze.json'
            freeze.write_text(json.dumps(self.policy(out)))
            sha=o.digest(freeze.read_bytes())
            result=o.run(freeze,sha,out)
            self.assertEqual(result['status'],'REFUSE_INVALID_OR_UNAVAILABLE_INPUT')
            self.assertTrue(result['attempt_consumed'])
            self.assertFalse(result['physical_obstruction'])
            self.assertTrue((out/'receipt.json').exists())
            with self.assertRaises(FileExistsError):o.run(freeze,sha,out)

    def test_policy_freeze_mutations(self):
        for field,value in [('attempt_limit',2),('mode','PASS'),('kind','v4'),
                            ('execution_files',{}),('review_sha256',''),('time_limit_seconds',1201)]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as directory:
                out=Path(directory)/'attempt';freeze=Path(directory)/'freeze.json'
                policy=self.policy(out);policy[field]=value;freeze.write_text(json.dumps(policy))
                with self.assertRaises(o.Refusal):o.run(freeze,o.digest(freeze.read_bytes()),out)
                self.assertFalse(out.exists())
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'freeze';p.write_text('{}')
            with self.assertRaises(o.Refusal):o.run(p,'wrong',Path(directory)/'out')

class ReworkTests(FreezeTests):
    def run_fixture(self,directory):
        out=Path(directory)/'attempt';freeze=Path(directory)/'freeze.json'
        freeze.write_text(json.dumps(self.policy(out)))
        return freeze,o.digest(freeze.read_bytes()),out

    def test_first_and_final_publication_failure(self):
        for failure_number in (1,2):
            with self.subTest(number=failure_number),tempfile.TemporaryDirectory() as directory:
                freeze,sha,out=self.run_fixture(directory)
                original=os.replace;counter=[0]
                def fail_once(source,destination):
                    if Path(destination).name=='receipt.json':
                        counter[0]+=1
                        if counter[0]==failure_number:
                            # The previous STARTED receipt survives the failed
                            # replacement; no truncation can corrupt it.
                            if failure_number==2:
                                self.assertEqual(json.loads((out/'receipt.json').read_text())['status'],'STARTED')
                            raise OSError('synthetic replace failure')
                    return original(source,destination)
                with patch.object(o.os,'replace',side_effect=fail_once):result=o.run(freeze,sha,out)
                self.assertEqual(result['status'],'REFUSE_PERSISTENCE')
                self.assertTrue(result['persistence_errors'])
                self.assertTrue(json.loads((out/'CONSUMED.json').read_text())['attempt_consumed'])
                self.assertEqual(json.loads((out/'receipt.json').read_text())['status'],'REFUSE_PERSISTENCE')
                with self.assertRaises(FileExistsError):o.run(freeze,sha,out)

    def test_marker_failure_and_cli_consumed_truth(self):
        with tempfile.TemporaryDirectory() as directory:
            freeze,sha,out=self.run_fixture(directory)
            original=o.atomic_publish
            def fail_marker(path,value):
                if Path(path).name=='CONSUMED.json':raise OSError('marker failed')
                return original(path,value)
            with patch.object(o,'atomic_publish',side_effect=fail_marker):
                with self.assertRaises(o.AttemptError) as raised:o.run(freeze,sha,out)
            self.assertTrue(o.cli_summary_error(raised.exception,out)['attempt_consumed'])
            self.assertFalse(json.loads((out/'fallback-receipt.json').read_text())['completed'])
            with self.assertRaises(FileExistsError):o.run(freeze,sha,out)

    def test_actual_hard_timeout_and_interrupted_child(self):
        for mode in ('blocked','interrupted'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                freeze,sha,out=self.run_fixture(directory)
                policy=json.loads(freeze.read_text());policy['time_limit_seconds']=1
                freeze.write_text(json.dumps(policy));sha=o.digest(freeze.read_bytes())
                def work(policy,receipt):
                    if mode=='blocked':time.sleep(60)
                    else:os._exit(7)
                    return receipt
                start=time.monotonic()
                with patch.object(o,'calculation',side_effect=work):result=o.run(freeze,sha,out)
                self.assertLess(time.monotonic()-start,3)
                self.assertIn(result['status'],('REFUSE_HARD_TIMEOUT','REFUSE_INTERRUPTED_CALCULATION'))
                self.assertTrue(result['attempt_consumed'])
                self.assertTrue(json.loads((out/'CONSUMED.json').read_text())['attempt_consumed'])
                self.assertNotIn('conditional_arithmetic',result)

    def test_supervisor_interruption_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            freeze,sha,out=self.run_fixture(directory)
            with patch.object(o,'execute_bounded',side_effect=KeyboardInterrupt):result=o.run(freeze,sha,out)
            self.assertEqual(result['status'],'REFUSE_INTERRUPTED')
            self.assertEqual(json.loads((out/'receipt.json').read_text())['status'],'REFUSE_INTERRUPTED')
            self.assertTrue((out/'CONSUMED.json').exists())

    def test_consumed_report_admission_no_certify_until_complete(self):
        # Metadata clone with tiny synthetic evidence bytes. No production raw
        # packet is opened, reconstructed or certified in these controls.
        report_path=Path('/Users/derekxwang/.codex/work-products/nvwa/2026-10-22-obstruction80/prerequisites/PREREQUISITES.json')
        template=json.loads(report_path.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);report=copy.deepcopy(template)
            mapping={}
            for i,row in enumerate(report['files']):
                path=root/('evidence'+str(i));path.write_text('synthetic'+str(i))
                mapping[row['path']]={'path':str(path),'bytes':path.stat().st_size,'sha256':o.digest(path.read_bytes())}
            def replace_rows(value):
                if isinstance(value,dict):
                    original_path=value.get('path')
                    result={k:replace_rows(v) for k,v in value.items()}
                    if original_path in mapping and all(k in value for k in ('bytes','sha256')):result.update(mapping[original_path])
                    return result
                if isinstance(value,list):return [replace_rows(v) for v in value]
                if isinstance(value,str) and value in mapping:return mapping[value]['path']
                return value
            report=replace_rows(report)
            assets={a['name']:a['source'] for a in report['assets']}
            report['support']['path']=next(r['path'] for r in report['files'] if r['path']==mapping[template['support']['path']]['path'])
            roles={'base':assets['base.obj'],'mhclo':assets['garment/female_sportsuit01.mhclo'],
                   'garment_obj':assets['garment/female_sportsuit01.obj'],
                   'support':mapping[template['support']['path']]}
            for mode in ('restored','empty','malformed','missing','false','duplicate','omitted','stale'):
                with self.subTest(mode=mode):
                    changed=copy.deepcopy(report);extras=copy.deepcopy(report['files'])
                    if mode=='missing':changed['claims'].pop(0)
                    if mode=='false':changed['claims'][0]['status']='UNKNOWN'
                    if mode=='duplicate':changed['claims'][1]=changed['claims'][0]
                    if mode=='omitted':extras.pop(0)
                    if mode=='empty':changed={}
                    raw=b'{' if mode=='malformed' else json.dumps(changed).encode()
                    path=root/'report.json';path.write_bytes(raw)
                    prereq={'path':str(path),'bytes':len(raw),'sha256':o.digest(raw)}
                    inputs={**roles,'prerequisites':prereq,'v4_freeze':prereq}
                    policy={'inputs':inputs,'supplemental_inputs':extras,'execution_files':o.inventory(Path(o.__file__).parent),
                            'old_v4_source_root':str(root)}
                    # Old309 authentication is replaced by an empty synthetic
                    # list only after admission. Real reconstruct/certify seam
                    # behavior remains monitored and the certificate is real.
                    freeze_path=root/'oldfreeze.json';freeze_path.write_text(json.dumps({'execution_files':[]}))
                    inputs['v4_freeze']={'path':str(freeze_path),'bytes':freeze_path.stat().st_size,'sha256':o.digest(freeze_path.read_bytes())}
                    if mode=='stale':
                        evidence=Path(extras[0]['path']);before=evidence.read_bytes();evidence.write_bytes(b'changed')
                    called=[]
                    def reconstruct_synthetic(inputs):
                        called.append('reconstruct');(root/('called-'+mode)).write_text('called')
                        return fixture(),{},{}
                    real_need=o.need
                    def need_synthetic(ok,message):
                        if message=='old closure omitted':return
                        return real_need(ok,message)
                    receipt={'coverage':{'arithmetic_witness_count':0},'status':'STARTED'}
                    pins={k:v['sha256'] for k,v in inputs.items() if k!='prerequisites'}
                    with patch.object(o,'PREREQ_SHA',o.digest(raw)),patch.object(o,'PINS',pins),\
                         patch.object(o,'reconstruct',side_effect=reconstruct_synthetic),patch.object(o,'need',side_effect=need_synthetic):
                        out=root/('attempt-'+mode)
                        runtime_policy=self.policy(out);runtime_policy.update(policy)
                        runtime=root/('runtime-'+mode+'.json');runtime.write_text(json.dumps(runtime_policy))
                        result=o.run(runtime,o.digest(runtime.read_bytes()),out)
                    if mode=='restored':
                        self.assertTrue((root/('called-'+mode)).exists())
                        self.assertEqual(result['conditional_arithmetic']['status'],'CONDITIONAL_STRICT_OBSTRUCTION')
                        self.assertEqual(result['status'],'REFUSE_MISSING_PREREQUISITE')
                    else:
                        self.assertFalse((root/('called-'+mode)).exists())
                        self.assertNotIn('conditional_arithmetic',result)
                    if mode=='stale':evidence.write_bytes(before)

if __name__=='__main__':unittest.main(verbosity=2)
