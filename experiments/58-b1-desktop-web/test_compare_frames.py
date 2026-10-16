"""Run real comparator CLI admission controls, also with Python optimization."""
import copy,importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
class FrameAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets=REPO/'.work/b1-pose-viewer/site/assets'
        actual=os.environ.get('B1_COMPARE_FIXTURE')
        if actual:
            value=json.loads(Path(actual).read_text());cls.frame=value.get('frame',value);cls.fixture_kind='actual captured viewer output'
        else:
            # Pure schema/invariant fixture for fresh CI. This is never reported
            # as B1 execution; local actual-output controls use the explicit env.
            identity=json.loads((cls.assets/'build-identity.json').read_text())
            rig=json.loads((cls.assets/'rig.game_engine.json').read_text())
            eye=[float(i%5==0) for i in range(16)]
            bones=[dict(name=name,parent=data['parent'] or None,**{key:eye[:] for key in ['rest','posed','inverse_bind','local_rest','local_posed','skin','canonical_rest','canonical_posed','frame_gauge']}) for name,data in rig.items()]
            parts={}
            for name,count in [('body',19158),('garment',1797)]:
                parts[name]=dict(source_vertex_ids=list(range(count)),positions=[[0.,0.,0.]]*count,rest_positions=[[0.,0.,0.]]*count,normals=[[0.,1.,0.]]*count,rest_normals=[[0.,1.,0.]]*count,tangents=[[1.,0.,0.,1.]]*count,joint_indices=[[0,0,0,0]]*count,joint_weights=[[1.,0.,0.,0.]]*count,full_joint_influences=None,bones=bones)
            cls.frame=dict(schema_version=1,common_manifest_sha256=identity['input_identity']['common_manifest_sha256'],actual_candidate_code_executed=True,actual_explicit_loader=True,gpu_vertex_readback=False,state=dict(format='nvwa-b1-pose-prototype',schema_version=1,recipe='neutral',pose='neutral',camera_yaw=0.,backend='gpu4'),build_identity=identity,parts=parts)
            cls.fixture_kind='synthetic invariant fixture, no execution claim'
        work=REPO/'.work/b1-pose-viewer';work.mkdir(parents=True,exist_ok=True)
        cls.temporary=tempfile.TemporaryDirectory(prefix='frame-controls-',dir=work);cls.out=Path(cls.temporary.name)
        cls.native=cls.out/'native.json';cls.native.write_text(json.dumps(cls.frame,allow_nan=False))
    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()
    def invoke(self,frame,label,optimized,both=False):
        web=self.out/(label+('-O' if optimized else '')+'.json');web.write_text(json.dumps(frame,allow_nan=False));output=web.with_suffix('.result.json');output.unlink(missing_ok=True)
        native=self.native
        if both:
            native=web.with_suffix('.native.json');native.write_text(json.dumps(frame,allow_nan=False))
        result=subprocess.run([sys.executable,*(['-O'] if optimized else []),str(ROOT/'compare_frames.py'),str(native),str(web),'--output',str(output)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        return result,output
    def test_complete_frame_passes_normal_and_optimized(self):
        for optimized in [False,True]:
            result,output=self.invoke(self.frame,'valid',optimized);self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertTrue(output.exists())
    def test_actual_gate_rejects_empty_missing_tampered_and_invalid_invariants(self):
        for fault in ['empty-parts','missing-garment','missing-bone','missing-source-id','position-10m','zero-normal','zero-gauge']:
            mutated=copy.deepcopy(self.frame)
            if fault=='empty-parts':mutated['parts']={}
            elif fault=='missing-garment':del mutated['parts']['garment']
            elif fault=='missing-bone':mutated['parts']['body']['bones']=mutated['parts']['body']['bones'][:-1]
            elif fault=='missing-source-id':mutated['parts']['body']['source_vertex_ids']=[0]*len(mutated['parts']['body']['source_vertex_ids'])
            elif fault=='position-10m':mutated['parts']['body']['positions'][0][0]+=10.
            elif fault=='zero-normal':mutated['parts']['body']['normals'][0]=[0.,0.,0.]
            elif fault=='zero-gauge':mutated['parts']['body']['bones'][0]['frame_gauge']=[0.]*16
            for optimized in [False,True]:
                result,output=self.invoke(mutated,fault,optimized,both=fault!='position-10m');self.assertNotEqual(result.returncode,0,(fault,optimized));self.assertFalse(output.exists(),(fault,optimized));self.assertIn('FRAME_PARITY_REJECTED',result.stdout)
if __name__=='__main__':unittest.main()
