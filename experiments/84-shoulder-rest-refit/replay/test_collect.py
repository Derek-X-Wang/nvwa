"""Structural and scoring-seam controls. Synthetic geometry is explicitly NOT-RUN."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import collect as c

RUN = 'unit-controls-only-not-a-capture'

def record(key):
    t, clip, k = key
    return {'kind':'matrix', 'run_id':RUN,
            'request':{'torso_length':t, 'jaw_drop':0, 'clip_id':clip, 'seconds':k/8, 'k':k},
            'snapshot':{'schema_version':1, 'profile_id':'nvwa-mpfb-b1-motion-v1', 'asset_id':c.diagnose.ASSET_ID, 'backend':{'type':'b1_cpu','schema_version':2,'asset_id':c.diagnose.ASSET_ID}, 'mode':'motion', 'parameters':{'torso_length':t,'jaw_drop':0},
                        'sample':{'timeline_id':'probe-entry', 'clip_id':clip, 'source_seconds':k/8, 'position_seconds':k/8, 'playing':False},
                        'bones':[{'name':str(i)} for i in range(53)], 'parts':[{'name':'body'},{'name':'garment'}]}}

def encoded(records):
    # Deliberately preserve noncanonical spaces and LF, rather than json.dumps rewriting.
    return [c.PREFIX + json.dumps(r, separators=(', ', ' : ')) + '\n' for r in records]

def rows():
    return [record(k) for k in c.RECIPES] + [{'kind':'complete','run_id':RUN,'matrix_samples':18}]

class CollectorControls(unittest.TestCase):
    def collect(self, records, directory):
        return c.collect(encoded(records),directory,RUN,lambda *_:{'synthetic_control_geometry':'NOT-RUN'})

    def reject(self, mutate):
        with tempfile.TemporaryDirectory() as d:
            data=rows(); mutate(data)
            with self.assertRaises((ValueError,KeyError,TypeError,IndexError)):
                self.collect(data,Path(d))

    def test_exact18_lossless_and_deterministic_gzip(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d); entries=self.collect(rows(),out)
            self.assertEqual(len(entries),18)
            raw=encoded(rows())[0][len(c.PREFIX):].encode()
            compressed=(out/entries[0]['path']).read_bytes()
            self.assertEqual(gzip.decompress(compressed),raw)
            self.assertEqual(compressed,gzip.compress(raw,mtime=0))
            self.assertEqual(entries[0]['raw_sha256'],c.digest(raw))

    def test_missing(self): self.reject(lambda x:x.pop(0))
    def test_duplicate(self): self.reject(lambda x:x.insert(0,copy.deepcopy(x[0])))
    def test_mislabeled_time(self): self.reject(lambda x:x[0]['request'].update(seconds=2))
    def test_malformed_snapshot(self): self.reject(lambda x:x[0].update(snapshot={}))
    def test_wrong_source_profile(self): self.reject(lambda x:x[0]['snapshot'].update(profile_id='nvwa-mpfb-b1-motion-v2'))
    def test_wrong_timeline(self): self.reject(lambda x:x[0]['snapshot']['sample'].update(timeline_id='arms'))
    def test_mixed_run(self): self.reject(lambda x:x[0].update(run_id='other-corpus'))
    def test_bool_index(self): self.reject(lambda x:x[0]['request'].update(k=False))
    def test_wrong_actual_parameters(self): self.reject(lambda x:x[0]['snapshot']['parameters'].update(jaw_drop=1))
    def test_unrequested_knee_frame(self): self.reject(lambda x:x[5]['request'].update(k=0,seconds=0))
    def test_duplicate_json_key(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
                c.collect([c.PREFIX+'{"kind":"matrix","kind":"matrix"}'],Path(d),RUN,lambda *_:None)

    def corpus(self, directory):
        entries=self.collect(rows(),directory)
        files=[{'path':'Cargo.toml','bytes':1,'sha256':c.digest(b'x')}]
        source={'files':files,'inventory_sha256':c.inventory_digest(files),'binary':{'bytes':4,'sha256':c.digest(b'unit')}}
        for name in ('before','at-run','after'):c.write_json(directory/f'source-{name}.json',source)
        anchor=directory/'anchor.json';anchor.write_bytes(b'unit anchor, not actual geometry')
        build={'schema_version':1,'kind':'nvwa84-completed-native-build-v1','status':'PASS_COMPLETED_BUILD','build_run_id':'unit-build-id','exit_code':0,'source_head':'0'*40,'source_files':files,'source_files_sha256':c.inventory_digest(files),'toolchain':{'rustc':'unit-rustc','cargo':'unit-cargo'},'host':{'system':'unit-os','machine':'unit-arch'},'command':['cargo','build','--locked','--offline'],'binary':{'name':'nvwa-shoulder-rest-replay',**source['binary']}}
        # Use nondefault formatting so receipt binding covers exact bytes.
        (directory/'build-receipt.json').write_bytes((json.dumps(build,indent=3)+'\n').encode())
        identity={'run_id':RUN,'schema':'NEW-current18-production-CPU-v1','source_inventory_sha256':source['inventory_sha256'],'fresh_nineteenth_sha256':c.digest(anchor.read_bytes()),'source_head':build['source_head'],'source_before_sha256':c.digest((directory/'source-before.json').read_bytes()),'build_command':build['command'],'build_run_id':build['build_run_id'],'build_receipt_sha256':c.digest((directory/'build-receipt.json').read_bytes()),'compiled_source_sha256':build['source_files_sha256'],'toolchain':build['toolchain'],'host':build['host'],'binary_sha256':source['binary']['sha256'],'binary_bytes':source['binary']['bytes']}
        c.write_json(directory/'identity.json',identity)
        manifest={'schema_version':1,'cohort_type':'hybrid-current18-original-anchor','historical_replay':'NOT-RUN_MISSING18','source_inventory_sha256':source['inventory_sha256'],'anchor':{'role':'authenticated-original-fresh-default','bytes':anchor.stat().st_size,'sha256':c.digest(anchor.read_bytes())},'status':'PASS_NEW_CURRENT18_CORPUS','run_id':RUN,'source_unchanged':True,'historical_input_hashes_reused':False,'cases':entries}
        self.bind_receipts(directory,manifest)
        return manifest,source,anchor

    def bind_receipts(self,directory,manifest):
        manifest['receipts']={key:c.receipt_row(directory,name) for key,name in {'identity':'identity.json','build':'build-receipt.json','source_before':'source-before.json','source_at_run':'source-at-run.json','source_after':'source-after.json'}.items()}
        c.write_json(directory/'manifest.json',manifest)

    def rebind_build(self,directory,manifest,build,update_identity=lambda x:None):
        c.write_json(directory/'build-receipt.json',build)
        identity=c.strict_load((directory/'identity.json').read_bytes())
        identity['build_receipt_sha256']=c.digest((directory/'build-receipt.json').read_bytes())
        update_identity(identity)
        c.write_json(directory/'identity.json',identity)
        self.bind_receipts(directory,manifest)

    def auth(self,directory,source,anchor):
        with patch.object(c,'FRESH_SHA',c.digest(anchor.read_bytes())):
            return c.authenticate_corpus(directory,c.digest((directory/'manifest.json').read_bytes()),source['inventory_sha256'],anchor)

    def test_scoring_seam_exact_corpus(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            self.assertEqual(len(self.auth(p,s,a)),18)

    def test_scoring_seam_tampered(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            (p/m['cases'][0]['path']).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'tampered compressed'):
                self.auth(p,s,a)

    def test_scoring_seam_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            (p/m['cases'][0]['path']).unlink()
            with self.assertRaises(OSError):self.auth(p,s,a)

    def test_scoring_seam_duplicate_even_with_rehashed_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p);m['cases'][1]=m['cases'][0]
            c.write_json(p/'manifest.json',m)
            with self.assertRaisesRegex(ValueError,'duplicate/mislabeled'):
                self.auth(p,s,a)

    def test_scoring_seam_wrong_frozen_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            with patch.object(c,'FRESH_SHA',c.digest(a.read_bytes())):
                with self.assertRaisesRegex(ValueError,'source'):
                    c.authenticate_corpus(p,c.digest((p/'manifest.json').read_bytes()),'wrong',a)

    def test_scoring_seam_changed_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            c.write_json(p/'source-after.json',{'different':True})
            with self.assertRaisesRegex(ValueError,'source_after receipt'):
                self.auth(p,s,a)

    def test_exact_fixture_mismatch_rejected_through_collector(self):
        data=rows()
        for row in data[:-1]:row['snapshot']['bones'][0]['matrix']=[1.0]
        data[0]['snapshot']['bones'][0]['matrix']=[1.00000001]
        def check(record,key):
            c.check_original_fixture(record['snapshot']['bones'],[{'name':'0','matrix':[1.0]}])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'EXACT original fixture'):
                c.collect(encoded(data),Path(d),RUN,check)

    def test_scoring_seam_tampered_identity_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            identity=c.strict_load((p/'identity.json').read_bytes());identity['toolchain']['rustc']='tampered'
            c.write_json(p/'identity.json',identity)
            with self.assertRaisesRegex(ValueError,'tampered identity receipt'):
                self.auth(p,s,a)

    def test_scoring_seam_tampered_build_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            raw=(p/'build-receipt.json').read_bytes();(p/'build-receipt.json').write_bytes(raw+b' ')
            with self.assertRaisesRegex(ValueError,'tampered build receipt'):
                self.auth(p,s,a)

    def test_scoring_seam_failed_build_even_with_rebound_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            build=c.strict_load((p/'build-receipt.json').read_bytes());build['exit_code']=1;build['status']='FAILED'
            self.rebind_build(p,m,build)
            with self.assertRaisesRegex(ValueError,'not completed success'):
                self.auth(p,s,a)

    def test_scoring_seam_wrong_binary_even_with_rebound_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            build=c.strict_load((p/'build-receipt.json').read_bytes());build['binary']['sha256']='wrong'
            self.rebind_build(p,m,build,lambda x:x.update(binary_sha256='wrong'))
            with self.assertRaisesRegex(ValueError,'completed build binary differs'):
                self.auth(p,s,a)

    def test_scoring_seam_toolchain_crosslink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            build=c.strict_load((p/'build-receipt.json').read_bytes());build['toolchain']['rustc']='different compiler'
            self.rebind_build(p,m,build)
            with self.assertRaisesRegex(ValueError,'toolchain differs'):
                self.auth(p,s,a)

    def test_scoring_seam_compiled_source_crosslink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            build=c.strict_load((p/'build-receipt.json').read_bytes());build['source_files'][0]['sha256']='wrong'
            self.rebind_build(p,m,build)
            with self.assertRaisesRegex(ValueError,'compiled source closure differs'):
                self.auth(p,s,a)

    def test_scoring_seam_build_capture_ids_cannot_be_conflated(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m,s,a=self.corpus(p)
            build=c.strict_load((p/'build-receipt.json').read_bytes());build['build_run_id']=RUN
            self.rebind_build(p,m,build,lambda x:x.update(build_run_id=RUN))
            with self.assertRaisesRegex(ValueError,'conflated'):
                self.auth(p,s,a)

if __name__=='__main__':unittest.main()
