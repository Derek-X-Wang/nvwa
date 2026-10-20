"""Portable called-seam guard tests. Synthetic fixture is not actual R2 validation."""
import copy,hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import validate_one as v,prepare_site as g
E=Path(__file__).resolve().parent
class ExplicitGuards(unittest.TestCase):
 def fixture(self,base):
  root=base/'validator';root.mkdir();files={}
  for i in range(311):
   name=f'sources/{i:03}.txt';p=root/name;p.parent.mkdir(exist_ok=True);raw=f'synthetic guard fixture {i}\n'.encode();p.write_bytes(raw);files[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
  receipt=base/'receipt.json';receipt.write_text(json.dumps({'files':files},sort_keys=True));digest=hashlib.sha256(receipt.read_bytes()).hexdigest();return root,receipt,digest
 def test_original_generator_output_exact_and_bad_inputs_rejected(self):
  old=(E/'original-index.html').read_text();self.assertEqual(g.generate(old).encode(),(E/'index.html').read_bytes())
  for bad in ['',old+' ',old.replace('TRANSFER_CORE_BEGIN','MISSING_CORE'),old.replace('try{api=await import(','wrong{api=await import(')]:
   with self.assertRaises(ValueError):g.generate(bad)
  with self.assertRaises(ValueError):g.core('no markers')
 def test_root_receipt_missing_empty_mutated_and_unsafe_lists_reject(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);root,receipt,digest=self.fixture(base);bound=json.loads(receipt.read_text());p=base/'mutated.json'
   # Patch only this explicit synthetic fixture's digest. CLI production pin stays hardcoded.
   with patch.object(v,'PINNED_ROOT_RECEIPT_SHA256',digest):
    v.verify_validator_root(root,receipt);missing=copy.deepcopy(bound);missing.pop('files');empty=copy.deepcopy(bound);empty['files']={};mutated=copy.deepcopy(bound);key=next(iter(mutated['files']));mutated['files'][key]['bytes']+=1;unsafe=copy.deepcopy(bound);item=unsafe['files'].pop(key);unsafe['files']['../escape']=item
    for value in [missing,empty,mutated,unsafe]:
     p.write_text(json.dumps(value))
     with self.assertRaises(ValueError):v.verify_validator_root(root,p)
    with self.assertRaises(FileNotFoundError):v.verify_validator_root(root,base/'missing.json')
 def test_actual_called_source_guard_rejects_synthetic_content_mutation(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);root,receipt,digest=self.fixture(base);clone=base/'clone';shutil.copytree(root,clone);p=clone/'sources/000.txt';p.write_bytes(p.read_bytes()+b'mutation red control')
   with patch.object(v,'PINNED_ROOT_RECEIPT_SHA256',digest),self.assertRaisesRegex(ValueError,'source drift'):v.verify_validator_root(clone,receipt)
 def test_independent_request_and_original_A_guards(self):
  envelope={'report':{'request_id':'independent-A'},'frame':{'request_id':'independent-A','candidate':{'variant':'AOriginal'}}};v.require_original_a(envelope,'independent-A')
  for value in ['', '../escape', None, 'x'*65]:
   with self.assertRaises(ValueError):v.expected_id(value)
  with self.assertRaisesRegex(ValueError,'ID mismatch'):v.require_original_a(envelope,'wrong-A')
  bad=copy.deepcopy(envelope);bad['frame']['candidate']['variant']='BLocalAlpha'
  with self.assertRaisesRegex(ValueError,'original A'):v.require_original_a(bad,'independent-A')
if __name__=='__main__':unittest.main()
