"""Candidate-independent red controls at evaluator entry/source validation seams."""
import argparse
import copy
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch
import evaluate_rest as evaluator

SOURCE=evaluator.ROOT/'assets/characters/mpfb-b1-v1/garment/female_sportsuit01.mhclo'

class ContractControls(unittest.TestCase):
    def changed(self):
        source=SOURCE.read_bytes()
        rows=evaluator.parse_mapping(source)
        lines=rows['lines'][:]
        row=rows['rows'][847]
        fields=row['fields'][:]
        fields[8]=str(float(fields[8])+.001)
        lines[row['line0']]=' '.join(fields)+'\n'
        return source,''.join(lines).encode()

    def test_entrypoint_refuses_scoring_before_root_freeze(self):
        args=argparse.Namespace(freeze=None,policy=Path('missing'),candidate=Path('missing'))
        with self.assertRaisesRegex(ValueError,'scoring disabled'):
            evaluator.run(args)

    def test_missing_mixed_and_tampered_actual_inputs_fail_at_loader(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            with self.assertRaisesRegex(ValueError,'missing/mixed/tampered actual input'):
                evaluator.authenticate_inputs(directory,directory/'fresh.json')
            ledger=evaluator.json.loads((evaluator.OLD/'input-hashes.json').read_text())['cases']
            first=directory/ledger[0]['case']
            # Same-size bytes and plausible gzip name cannot replace original input.
            first.write_bytes(b'0'*ledger[0]['bytes'])
            with self.assertRaisesRegex(ValueError,'missing/mixed/tampered actual input'):
                evaluator.authenticate_inputs(directory,directory/'fresh.json')
            # A different actual case name cannot satisfy this case's byte identity.
            first.unlink()
            (directory/ledger[1]['case']).write_bytes(b'other-case')
            with self.assertRaisesRegex(ValueError,'missing/mixed/tampered actual input'):
                evaluator.authenticate_inputs(directory,directory/'fresh.json')

    def test_new_cohort_freeze_schema_and_bounds_are_not_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory);policy_path=directory/'policy.json';freeze_path=directory/'freeze.json'
            policy={'thresholds':evaluator.THRESHOLDS,'input_hashes_sha256':evaluator.INPUTS_SHA,
                    'cohort_kind':evaluator.COHORT_KIND,'cohort_manifest_sha256':'a'*64,
                    'source_inventory_sha256':'b'*64,'baseline_rest_bound_m':1e-7,'baseline_posed_bound_m':1e-5}
            def write():
                policy_path.write_text(evaluator.json.dumps(policy))
                freeze={'status':'FROZEN_BASELINE_PREFLIGHT','candidate_count':1,
                        'policy_sha256':evaluator.digest(policy_path),
                        **{k:policy[k] for k in ('cohort_kind','cohort_manifest_sha256','source_inventory_sha256')}}
                files=[{'path':name,'bytes':(evaluator.ROOT/name).stat().st_size,
                        'sha256':evaluator.digest(evaluator.ROOT/name)} for name in evaluator.required_execution_paths()]
                freeze['execution_files']=files
                freeze['execution_files_sha256']=evaluator.hashlib.sha256(evaluator.json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                freeze_path.write_text(evaluator.json.dumps(freeze))
            write()
            evaluator.validate_freeze(freeze_path,policy_path,preflight=True)
            policy['cohort_kind']=evaluator.WASM_COHORT_KIND;write()
            evaluator.validate_freeze(freeze_path,policy_path,preflight=True)
            policy['cohort_kind']=evaluator.COHORT_KIND;write()
            with self.assertRaisesRegex(ValueError,'freeze invalid'):
                evaluator.validate_freeze(freeze_path,policy_path,preflight=False)
            policy['baseline_rest_bound_m']=1e-6;write()
            with self.assertRaisesRegex(ValueError,'reconstruction bounds'):
                evaluator.validate_freeze(freeze_path,policy_path,preflight=True)
            policy['baseline_rest_bound_m']=1e-7;policy['cohort_kind']='historical19';write()
            with self.assertRaisesRegex(ValueError,'hybrid cohort kind'):
                evaluator.validate_freeze(freeze_path,policy_path,preflight=True)

    def test_offset_only_source_change_is_allowed(self):
        old,new=self.changed()
        a,b,changed=evaluator.validate_source_change(old,new,[847])
        self.assertEqual(changed,[847])
        self.assertEqual(a['rows'][847]['weights'],b['rows'][847]['weights'])

    def test_changed_helper_signed_weight_body_mask_and_outside_row_reject(self):
        old,new=self.changed()
        mutations=[new.replace(b'delete_verts',b'delete_vertex',1),
                   new.replace(b'x_scale 5399',b'x_scale 5398',1)]
        mapping=evaluator.parse_mapping(new)
        for sid,field in [(847,0),(847,3),(846,8)]:
            lines=mapping['lines'][:]
            row=mapping['rows'][sid]
            fields=row['fields'][:]
            fields[field]=str(float(fields[field])+1) if field else str(int(fields[field])+1)
            lines[row['line0']]=' '.join(fields)+'\n'
            mutations.append(''.join(lines).encode())
        for mutated in mutations:
            with self.subTest(mutated_sha=evaluator.hashlib.sha256(mutated).hexdigest()):
                with self.assertRaises(ValueError):
                    evaluator.validate_source_change(old,mutated,[847])

    def test_original_source_tamper_is_rejected(self):
        old,new=self.changed()
        with self.assertRaisesRegex(ValueError,'original garment source hash'):
            evaluator.validate_source_change(old+b'\n',new,[847])

    def test_supported_row_whitespace_line_ending_and_other_tokens_are_byte_fixed(self):
        old,new=self.changed()
        mapping=evaluator.parse_mapping(new);line=mapping['rows'][847]['line0']
        for replacement in (mapping['lines'][line].replace(' ','  ',1),
                            mapping['lines'][line].rstrip('\n')+'\r\n',
                            mapping['lines'][line].replace(' ','\t',6)):
            lines=mapping['lines'][:];lines[line]=replacement
            with self.assertRaisesRegex(ValueError,'exact offset token spans'):
                evaluator.validate_source_change(old,''.join(lines).encode(),[847])

    def test_execution_tamper_and_missing_helper_reject_at_real_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory);helper=directory/'experiments/test/helper.py'
            helper.parent.mkdir(parents=True);helper.write_bytes(b'original helper')
            row={'path':'experiments/test/helper.py','bytes':helper.stat().st_size,'sha256':evaluator.digest(helper)}
            freeze={'execution_files':[row]}
            freeze['execution_files_sha256']=evaluator.hashlib.sha256(evaluator.json.dumps([row],sort_keys=True,separators=(',',':')).encode()).hexdigest()
            with patch.object(evaluator,'ROOT',directory),patch.object(evaluator,'EXECUTION_DIRECTORIES',('test',)):
                self.assertEqual(evaluator.verify_execution(freeze),freeze['execution_files_sha256'])
                helper.write_bytes(b'changed helper!')
                with self.assertRaisesRegex(ValueError,'execution source bytes differ'):
                    evaluator.verify_execution(freeze)
                helper.write_bytes(b'original helper')
                (helper.parent/'new-import.py').write_bytes(b'new helper')
                with self.assertRaisesRegex(ValueError,'source closure incomplete'):
                    evaluator.verify_execution(freeze)

    def test_source_reconstruction_explicitly_applies_stored_f32_morph(self):
        neutral={i:[1.,1.,1.] for i in range(19158)};neutral[1]=[2.,2.,2.]
        shaped=copy.deepcopy(neutral);shaped[0]=[evaluator.f32(1e-8)]*3
        mapping={'scales':{key:(0,1,1.) for key in 'xyz'},
                 'rows':[{'helpers':[0],'weights':[1.],'offset':[0.,0.,0.]}]}
        def raw(parameters):return neutral if parameters['torso_length']==0 else shaped
        with patch.object(evaluator,'raw_cage',side_effect=raw):
            reconstructed,_=evaluator.reconstruct_source(mapping,{'torso_length':1,'jaw_drop':0})
        self.assertNotEqual(shaped[0],[0.,0.,0.])
        self.assertEqual(reconstructed['body'][0],[0.,0.,0.])
        self.assertEqual(reconstructed['garment'][0],[0.,0.,0.])
        # Disabling the actual morph stage cannot silently preserve these expected results.
        with patch.object(evaluator,'raw_cage',side_effect=raw), \
             patch.object(evaluator,'morph_roundtrip',side_effect=lambda base,shape:shape):
            bypassed,_=evaluator.reconstruct_source(mapping,{'torso_length':1,'jaw_drop':0})
        self.assertNotEqual(bypassed['garment'],reconstructed['garment'])

    def test_both_direct_posed_checks_gate_original_anchor_role(self):
        from types import SimpleNamespace
        identity=[float(i%5==0) for i in range(16)]
        part={'name':'body','source_ids':[0],'rest_positions':[[0.,0.,0.]],
              'positions':[[0.,0.,0.]],'full_joint_influences':[[(0,1.)]]}
        checker=SimpleNamespace(source_weights={0:{'bone':1.}})
        skin=[[[float(i==j) for j in range(4)] for i in range(4)]]
        def check():return evaluator.check_baseline_part(part,[[0.,0.,0.]],[{'skin':identity}],
                                  checker,['bone'],skin,'original-fresh-default-anchor/body')
        metrics=check()
        self.assertEqual(metrics['scalar_f32_PreparedSkin_matrix_blend']['exact_component_count'],3)
        self.assertEqual(metrics['independent_source_weights_FK_binary64_LBS']['component_count'],3)
        with patch.object(evaluator.corpus,'independent_lbs',return_value=[[1e-4,0.,0.]]):
            with self.assertRaisesRegex(ValueError,'source/FK/binary64 LBS.*original-fresh-default-anchor'):
                check()
        with patch.object(evaluator,'full_positive_skin',return_value=[[1e-4,0.,0.]]):
            with self.assertRaisesRegex(ValueError,'scalar-f32 PreparedSkin.*original-fresh-default-anchor'):
                check()

    def test_actual_fitting_uses_case_scales_and_signed_weights(self):
        mapping={'scales':{'x':(0,1,2.),'y':(0,1,4.),'z':(0,1,8.)},
                 'rows':[{'helpers':[0,1], 'weights':[2.,-1.], 'offset':[1.,1.,1.]}]}
        fitted,scales=evaluator.fit_rows(mapping,{0:[0.,0.,0.],1:[2.,8.,32.]})
        self.assertEqual(scales,[1.,2.,4.])
        self.assertEqual(fitted,[[-1.,-6.,-28.]])
        with self.assertRaisesRegex(ValueError,'reference absent'):
            evaluator.fit_rows(mapping,{0:[0.,0.,0.]})

    def test_skin_retains_five_positive_aggregates_and_rejects_zero(self):
        matrices=[]
        for i in range(5):
            matrix=[float(j%5==0) for j in range(16)]
            matrix[12]=float(i)
            matrices.append({'skin':matrix})
        row=[(i,1.) for i in range(5)]
        posed=evaluator.full_positive_skin([[1.,2.,3.]],[row],matrices)
        self.assertEqual(posed,[[3.,2.,3.]])
        with self.assertRaisesRegex(ValueError,'positive'):
            evaluator.full_positive_skin([[1.,2.,3.]],[[(0,0.)]],matrices)

if __name__=='__main__': unittest.main()
