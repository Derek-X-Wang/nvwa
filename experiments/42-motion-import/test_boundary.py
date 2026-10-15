"""CLI integration controls: every rejection enters the actual Rust importer."""
import copy,hashlib,json,os,struct,subprocess,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];FIX=HERE/'fixtures';PRIVATE=ROOT/'.work/m2-import';BINARY=PRIVATE/'target/debug/nvwa-motion-import-experiment';BASE=ROOT/'assets/fixtures/nvwa-humanoid.glb'
def encode(v):return json.dumps(v,separators=(',',':')).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
class Boundary(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=PRIVATE);self.d=Path(self.temp.name);self.raw=json.loads((FIX/'authored.raw.json').read_bytes());self.env=json.loads((FIX/'authored.normalized.json').read_bytes());self.saved=self.d/'current.nvwa.json';self.saved.write_bytes(b'current Work must stay unchanged');self.before=self.saved.read_bytes()
    def tearDown(self):self.assertEqual(self.saved.read_bytes(),self.before);self.temp.cleanup()
    def run_import(self,raw=None,env=None,base=None,out=None,raw_bytes=None,env_bytes=None):
        r=encode(self.raw if raw is None else raw) if raw_bytes is None else raw_bytes;e=copy.deepcopy(self.env if env is None else env);e.update({k:v for k,v in (self.raw if raw is None else raw).items()});e['provenance']['raw_sha256']=sha(r)
        (self.d/'raw.json').write_bytes(r);(self.d/'norm.json').write_bytes(encode(e)if env_bytes is None else env_bytes)
        out=out or self.d/'output';p=subprocess.run([str(BINARY),str(self.d/'norm.json'),str(self.d/'raw.json'),str(base or BASE),str(out)],capture_output=True,text=True);return p,out
    def rejected(self,raw=None,**kw):
        p,out=self.run_import(raw,**kw);self.assertNotEqual(p.returncode,0,p.stdout);self.assertFalse(out.exists());return p.stderr
    def test_valid_authored_actual_clip(self):
        p,out=self.run_import(env_bytes=json.dumps(self.env,indent=2).encode());self.assertEqual(p.returncode,0,p.stderr);m=json.loads((out/'manifest.json').read_bytes());self.assertEqual(m['provenance_kind'],'authored_control');self.assertFalse(m['genuine_inference_verified']);self.assertFalse(m['ai_generated']);self.assertLessEqual((out/'normalized.json').stat().st_size,4<<20);self.assertEqual(m['frame_count'],73);self.assertEqual(m['clip_sha256'],sha((out/'clip.glb').read_bytes()));self.assertEqual(m['input_normalized_sha256'],sha((self.d/'norm.json').read_bytes()));self.assertEqual(m['output_normalized_sha256'],sha((out/'normalized.json').read_bytes()));self.assertNotEqual(m['input_normalized_sha256'],m['output_normalized_sha256']);self.assertNotIn('normalized_sha256',m)
    def test_malformed_frames_and_joint_arrays(self):
        for key in ['local_rotations_xyzw','root_translations_m']:
            r=copy.deepcopy(self.raw);r[key].pop();self.rejected(r)
        r=copy.deepcopy(self.raw);r['local_rotations_xyzw'][0].pop();self.rejected(r)
    def test_wrong_joint_order_rejected_against_real_base(self):
        r=copy.deepcopy(self.raw);r['skeleton']['joint_names'][1:3]=reversed(r['skeleton']['joint_names'][1:3]);self.assertIn('joint order',self.rejected(r))
    def test_unknown_axes_units_order_space(self):
        for key,value in [('up_axis','Z'),('handedness','left'),('rotation_order','wxyz'),('units','centimeters'),('transform_space','global'),('root_motion_mode','delta')]:
            r=copy.deepcopy(self.raw);r['convention'][key]=value;self.rejected(r)
    def test_duplicate_top_and_nested_keys(self):
        rb=encode(self.raw)
        self.rejected(raw_bytes=rb[:-1]+b',"schema_version":1}')
        eb=encode(self.env).replace(b'"units":"meters"',b'"units":"meters","units":"meters"');self.rejected(env_bytes=eb)
    def test_truncated_raw_and_glb(self):
        self.rejected(raw_bytes=encode(self.raw)[:-3]);base=self.d/'truncated.glb';base.write_bytes(BASE.read_bytes()[:-5]);self.rejected(base=base)
    def test_nonfinite_and_invalid_quats(self):
        for v in [[0,0,0,0],[0,0,0,2],[float('nan'),0,0,1],[float('inf'),0,0,1]]:
            r=copy.deepcopy(self.raw);r['local_rotations_xyzw'][0][0]=v;self.rejected(r)
    def test_hierarchy_root_cycles_and_names(self):
        for value in [[None]*18,[0]+list(range(17)),[None,99]+[0]*16]:
            r=copy.deepcopy(self.raw);r['skeleton']['parent_indices']=value;self.rejected(r)
        r=copy.deepcopy(self.raw);r['skeleton']['joint_names'][1]=r['skeleton']['joint_names'][0];self.rejected(r)
    def test_rest_scales_and_rest_mismatch(self):
        for v in [0,-1,float('nan')]:
            r=copy.deepcopy(self.raw);r['skeleton']['rest_local_scales_xyz'][0][0]=v;self.rejected(r)
        r=copy.deepcopy(self.raw);r['skeleton']['rest_local_translations_m'][1][0]+=0.01;self.rejected(r)
    def test_time_bounds_monotonicity_and_f32_collapse(self):
        for times in [[0,0],[.1,.2],[0,5.1],[0,float('nan')],[0,1,1+1e-10]]:
            r=copy.deepcopy(self.raw);r['sample_times_seconds']=times;self.rejected(r)
        r=copy.deepcopy(self.raw);r['sample_times_seconds']=[i/151 for i in range(152)];self.rejected(r)
    def test_unknown_schema_skeleton_and_fields(self):
        r=copy.deepcopy(self.raw);r['schema_version']=2;self.rejected(r)
        r=copy.deepcopy(self.raw);r['skeleton']['identity']='unknown30';self.rejected(r)
        r=copy.deepcopy(self.raw);r['extra']='unsupported';self.rejected(r)
    def test_generated_claim_cannot_unlock_with_manifest(self):
        r=copy.deepcopy(self.raw);r['provenance_kind']='generated';self.assertIn('real raw-output/run provenance',self.rejected(r))
        e=copy.deepcopy(self.env);e['provenance']['provider']='pretend';self.rejected(env=e)
    def test_forged_receipt_cannot_authenticate_generation(self):
        raw=copy.deepcopy(self.raw);raw['provenance_kind']='generated';rb=encode(raw);receipt=encode({'status':'succeeded','exit_code':0,'raw_sha256':sha(rb)})
        env={**raw,'provenance':{**self.env['provenance'],'raw_sha256':sha(rb),'run_receipt_sha256':sha(receipt),'provider':'synthetic-fake-provider','code_revision':'synthetic-fake-revision','model_sha256':'0'*64}}
        (self.d/'raw.json').write_bytes(rb);(self.d/'norm.json').write_bytes(encode(env));(self.d/'receipt.json').write_bytes(receipt)
        p=subprocess.run([str(BINARY),str(self.d/'norm.json'),str(self.d/'raw.json'),str(BASE),str(self.d/'output'),str(self.d/'receipt.json')],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0);self.assertIn('generated_evidence_unavailable',p.stderr);self.assertFalse((self.d/'output').exists())
    def test_raw_hash_and_payload_binding(self):
        e=encode(self.env).replace(self.env['provenance']['raw_sha256'].encode(),b'0'*64);self.rejected(env_bytes=e)
        r=copy.deepcopy(self.raw);r['root_translations_m'][0][0]=.2;e=copy.deepcopy(self.env);e['provenance']['raw_sha256']=sha(encode(r));self.rejected(raw=r,env_bytes=encode(e))
    def test_existing_destination_and_unrelated_file_preserved(self):
        out=self.d/'output';out.mkdir();sentinel=out/'unrelated.txt';sentinel.write_bytes(b'never overwrite');p,_=self.run_import(out=out);self.assertNotEqual(p.returncode,0);self.assertEqual(sentinel.read_bytes(),b'never overwrite');self.assertEqual(list(out.iterdir()),[sentinel])
    def test_json_size_limit_and_symlink_input(self):
        self.rejected(raw_bytes=b' '*((4<<20)+1));symlink=self.d/'link.glb';symlink.symlink_to(BASE);self.assertIn('non-symlink',self.rejected(base=symlink))
    def adapt(self,side=None,roots=None,rots=None):
        (self.d/'side.json').write_bytes(encode(json.loads((FIX/'synthetic-f32.sidecar.json').read_bytes())if side is None else side));(self.d/'root.f32').write_bytes((FIX/'synthetic-root_positions.f32').read_bytes()if roots is None else roots);(self.d/'rot.f32').write_bytes((FIX/'synthetic-local_rotations_xyzw.f32').read_bytes()if rots is None else rots)
        return subprocess.run([str(BINARY),'adapt-f32',str(self.d/'side.json'),str(self.d/'root.f32'),str(self.d/'rot.f32'),str(self.d/'adapted')],capture_output=True,text=True)
    def test_f32_authored_byte_control_root_height_independent(self):
        p=self.adapt();self.assertEqual(p.returncode,0,p.stderr);r=json.loads((self.d/'adapted/raw.json').read_bytes());self.assertAlmostEqual(r['root_translations_m'][0][1],.9,6);self.assertEqual(r['skeleton']['rest_local_translations_m'][0][1],.988);self.assertEqual(r['provenance_kind'],'authored_control')
    def test_f32_truncated_extra_nonfinite_and_wrong_layout(self):
        root=(FIX/'synthetic-root_positions.f32').read_bytes()
        for b in [root[:-1],root+b'\0',struct.pack('<f',float('nan'))+root[4:]]:
            p=self.adapt(roots=b);self.assertNotEqual(p.returncode,0);self.assertFalse((self.d/'adapted').exists())
        for key,value in [('endianness','big'),('frame_count',90),('joint_count',77),('code_revision','unknown')]:
            side=json.loads((FIX/'synthetic-f32.sidecar.json').read_bytes());side[key]=value;p=self.adapt(side=side);self.assertNotEqual(p.returncode,0)
    def test_soma_structural_output_requires_retargeting(self):
        self.assertEqual(self.adapt().returncode,0);p=subprocess.run([str(BINARY),str(self.d/'adapted/normalized.json'),str(self.d/'adapted/raw.json'),str(BASE),str(self.d/'output')],capture_output=True,text=True);self.assertNotEqual(p.returncode,0);self.assertIn('retargeting required',p.stderr);self.assertFalse((self.d/'output').exists())
if __name__=='__main__':unittest.main(verbosity=2)
