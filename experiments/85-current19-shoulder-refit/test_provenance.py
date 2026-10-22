"""Temporary synthetic provenance controls; no actual baseline/candidate evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import current19 as c
import provenance as p
from test_current19 import rows, encoded, RUN


class BuildControls(unittest.TestCase):
    def fixture(self,root):
        for name in p.capture_paths(root):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(name.encode())
        binary=root/'unit-binary';binary.write_bytes(b'unit-binary-not-compiled')
        source=p.source_inventory(binary,root)
        build={'schema_version':1,'kind':p.BUILD_KIND,'status':'PASS_COMPLETED_BUILD','exit_code':0,
               'build_run_id':'synthetic-build','source_head':'0'*40,'target':'aarch64-apple-darwin',
               'toolchain':{'rustc':'unit-rustc','cargo':'unit-cargo'},
               'host':{'system':'Darwin','machine':'arm64','node':'synthetic-host'},
               'build_config':{'offline':True,'locked':True},
               'command':['cargo','build','--offline','--locked'],
               'binary':{'name':'nvwa-current19-replay',**source['binary']},
               'source_files':p.rows_for(root,p.compiled_paths(root))}
        build['source_files_sha256']=p.inventory_digest(build['source_files'])
        identity={'run_id':'synthetic-capture','capture_run_id':'synthetic-capture',
                  'build_run_id':build['build_run_id'],'build_command':build['command'],
                  'source_head':build['source_head'],'target':build['target'],
                  'toolchain':copy.deepcopy(build['toolchain']),'host':copy.deepcopy(build['host']),
                  'build_config':copy.deepcopy(build['build_config']),'binary':source['binary'],
                  'compiled_source_sha256':build['source_files_sha256']}
        return source,build,identity

    def reject(self,mutate):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source,build,identity=self.fixture(root)
            mutate(root,source,build,identity)
            with self.assertRaises((ValueError,KeyError,TypeError)):
                p.check_build(build,source,identity,root)

    def test_exact_completed_closure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source,build,identity=self.fixture(root)
            p.check_build(build,source,identity,root)
            self.assertNotEqual(build['build_run_id'],identity['run_id'])

    def test_failed_build(self):self.reject(lambda r,s,b,i:b.update(exit_code=1))
    def test_bool_exit(self):self.reject(lambda r,s,b,i:b.update(exit_code=False))
    def test_absent_command(self):self.reject(lambda r,s,b,i:b.update(command=[]))
    def test_wrong_target(self):self.reject(lambda r,s,b,i:b.update(target='wasm32-unknown-unknown'))
    def test_wrong_toolchain(self):self.reject(lambda r,s,b,i:b['toolchain'].update(rustc='other'))
    def test_wrong_host(self):self.reject(lambda r,s,b,i:b['host'].update(machine='x86_64'))
    def test_wrong_host_node(self):self.reject(lambda r,s,b,i:b['host'].update(node='other-host'))
    def test_wrong_config(self):self.reject(lambda r,s,b,i:b['build_config'].update(locked=False))
    def test_wrong_binary(self):self.reject(lambda r,s,b,i:b['binary'].update(sha256='0'*64))
    def test_wrong_source_head(self):self.reject(lambda r,s,b,i:b.update(source_head='1'*40))
    def test_mixed_run(self):self.reject(lambda r,s,b,i:i.update(build_run_id=i['run_id']))
    def test_missing_closure(self):self.reject(lambda r,s,b,i:b['source_files'].pop())
    def test_duplicate_closure(self):self.reject(lambda r,s,b,i:b['source_files'].append(b['source_files'][0]))
    def test_escaped_source(self):self.reject(lambda r,s,b,i:b['source_files'][0].update(path='../escape'))
    def test_modified_actual_source(self):self.reject(lambda r,s,b,i:(r/'Cargo.toml').write_bytes(b'mutated'))
    def test_wrong_inventory_digest(self):self.reject(lambda r,s,b,i:b.update(source_files_sha256='0'*64))
    def test_future_adapter_has_separate_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source,build,identity=self.fixture(root)
            before=p.capture_paths(root)
            (root/'experiments/85-current19-shoulder-refit/future_author.py').write_text('not capture code')
            self.assertEqual(before,p.capture_paths(root))
            p.check_build(build,source,identity,root)


class Paths(unittest.TestCase):
    def test_paths(self):
        for name in ('../escape','/absolute','a/../b','a//b','a/./b',''):
            with self.assertRaises(ValueError):c.safe_path(Path('/tmp'),name)


class CorpusControls(unittest.TestCase):
    def write(self,path,value):path.write_text(json.dumps(value,indent=2)+'\n')

    def fixture(self,directory):
        root=directory/'source';root.mkdir()
        source,build,identity=BuildControls().fixture(root)
        out=directory/'corpus';out.mkdir()
        data=rows();data[-2]['snapshot']['generation']=2
        entries=c.collect(encoded(data),out,RUN)
        self.write(out/'geometry-audit.json',c.audit_geometry(data[:-1],lambda _:{'synthetic_geometry':'NOT-RUN'}))
        self.write(out/'build-receipt.json',build)
        for name in ('before','at-run','after'):self.write(out/f'source-{name}.json',source)
        authorization={'status':'FROZEN_FOR_CURRENT19_CAPTURE','cohort_kind':c.KIND,
                       'source_inventory_sha256':source['inventory_sha256'],'binary':source['binary'],
                       'build_receipt_sha256':c.digest((out/'build-receipt.json').read_bytes())}
        self.write(out/'capture-authorization.json',authorization)
        identity.update(cohort_kind=c.KIND,run_id=RUN,capture_run_id=RUN,
                        source_inventory_sha256=source['inventory_sha256'],
                        source_before_sha256=c.digest((out/'source-before.json').read_bytes()),
                        build_receipt_sha256=c.digest((out/'build-receipt.json').read_bytes()),
                        capture_authorization_sha256=c.digest((out/'capture-authorization.json').read_bytes()))
        self.write(out/'identity.json',identity)
        manifest={'schema_version':1,'cohort_kind':c.KIND,'status':'PASS_CURRENT19_BASELINE',
                  'source_unchanged':True,'source_inventory_sha256':source['inventory_sha256'],
                  'historical_raw_identity_reused':False,'quality_acceptance':False,
                  'producer_exit_code':0,'run_id':RUN,'cases':entries,
                  'retained_raw_records':[p.receipt_row(out,f'raw/{i:02d}.json') for i in range(20)],
                  'receipts':{key:p.receipt_row(out,name) for key,name in p.RECEIPTS.items()}}
        self.write(out/'manifest.json',manifest)
        return root,out,source,manifest

    def auth(self,root,out,source):
        return p._authenticate(out,c.digest((out/'manifest.json').read_bytes()),source['inventory_sha256'],root)

    def reject(self,mutate):
        with tempfile.TemporaryDirectory() as d:
            root,out,source,manifest=self.fixture(Path(d))
            mutate(root,out,source,manifest)
            self.write(out/'manifest.json',manifest)
            with self.assertRaises((ValueError,KeyError,TypeError,OSError,IndexError)):
                self.auth(root,out,source)

    def test_exact_lossless_readback(self):
        with tempfile.TemporaryDirectory() as d:
            root,out,source,manifest=self.fixture(Path(d))
            self.assertEqual(len(self.auth(root,out,source)),19)

    def test_frozen_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root,out,source,manifest=self.fixture(Path(d))
            with self.assertRaisesRegex(ValueError,'manifest differs'):
                p._authenticate(out,'0'*64,source['inventory_sha256'],root)

    def test_tampered_gzip(self):self.reject(lambda r,o,s,m:(o/m['cases'][0]['path']).write_bytes(b'tampered'))
    def test_missing_case(self):self.reject(lambda r,o,s,m:(o/m['cases'][0]['path']).unlink())
    def test_manifest_duplicate_case(self):self.reject(lambda r,o,s,m:m['cases'].__setitem__(1,m['cases'][0]))
    def test_manifest_escaped_path(self):self.reject(lambda r,o,s,m:m['cases'][0].update(path='../escape'))
    def test_tampered_raw_digest(self):self.reject(lambda r,o,s,m:m['cases'][0].update(raw_sha256='0'*64))
    def test_tampered_identity(self):self.reject(lambda r,o,s,m:(o/'identity.json').write_bytes(b'{}'))
    def test_tampered_build_receipt(self):self.reject(lambda r,o,s,m:(o/'build-receipt.json').write_bytes(b'{}'))
    def test_tampered_authorization(self):self.reject(lambda r,o,s,m:(o/'capture-authorization.json').write_bytes(b'{}'))
    def test_tampered_source_after(self):self.reject(lambda r,o,s,m:(o/'source-after.json').write_bytes(b'{}'))
    def test_source_changed_after_capture(self):self.reject(lambda r,o,s,m:(r/'Cargo.toml').write_bytes(b'changed'))
    def test_failed_producer(self):self.reject(lambda r,o,s,m:m.update(producer_exit_code=2))
    def test_unadmitted(self):self.reject(lambda r,o,s,m:m.update(status='REJECT_CURRENT19_BASELINE'))
    def test_historical_relabel(self):self.reject(lambda r,o,s,m:m.update(historical_raw_identity_reused=True))
    def test_false_quality_claim(self):self.reject(lambda r,o,s,m:m.update(quality_acceptance=True))
    def test_missing_raw_manifest(self):self.reject(lambda r,o,s,m:m.pop('retained_raw_records'))
    def test_missing_raw_file(self):self.reject(lambda r,o,s,m:(o/'raw/00.json').unlink())
    def test_missing_raw_completion_file(self):self.reject(lambda r,o,s,m:(o/'raw/19.json').unlink())
    def test_raw_tamper(self):self.reject(lambda r,o,s,m:(o/'raw/00.json').write_bytes(b'{}'))
    def test_completion_truncated(self):self.reject(lambda r,o,s,m:(o/'raw/19.json').write_bytes(b'{'))
    def test_raw_receipts_reordered(self):
        self.reject(lambda r,o,s,m:m['retained_raw_records'].__setitem__(slice(0,2),m['retained_raw_records'][1::-1]))
    def replace_raw(self,out,manifest,index,change):
        path=out/'raw'/f'{index:02d}.json';record=c.strict_load(path.read_bytes());change(record)
        self.write(path,record);manifest['retained_raw_records'][index]=p.receipt_row(out,str(path.relative_to(out)))
    def test_rehashed_wrong_completion_count(self):
        self.reject(lambda r,o,s,m:self.replace_raw(o,m,19,lambda x:x.update(samples=18)))
    def test_rehashed_wrong_completion_order(self):
        self.reject(lambda r,o,s,m:self.replace_raw(o,m,19,lambda x:x['cases'].reverse()))
    def test_rehashed_raw_gzip_disagreement(self):
        self.reject(lambda r,o,s,m:self.replace_raw(o,m,0,lambda x:x['snapshot'].update(character_entity='different-valid-publication')))
    def test_extra_raw_file(self):self.reject(lambda r,o,s,m:(o/'raw/20.json').write_bytes(b'{}'))
    def test_geometry_audit_tamper(self):self.reject(lambda r,o,s,m:(o/'geometry-audit.json').write_bytes(b'{}'))


if __name__=='__main__':unittest.main()
