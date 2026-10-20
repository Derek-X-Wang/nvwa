"""Portable guard fixtures. Actual source oracle is a separate explicit command."""
import copy,json,tempfile,unittest
from pathlib import Path
from source_root import verify_validator_root,expected_id
from validate_aba import restoration
class Validation(unittest.TestCase):
 def test_restoration_exact_exclusions(self):
  a={'report':{'request_id':'a','work_json':'{}','current':True},'frame':{'request_id':'a','stable_updates':2,'identity':{'camera':[1,2]},'candidate':{'image':'A'}}};b=copy.deepcopy(a);b['report']['request_id']='a2';b['frame'].update(request_id='a2',stable_updates=3);restoration(a,b)
  for part,key,value in [('report','work_json','changed'),('report','current',False),('frame','identity',{'camera':[9]}),('frame','candidate',{'image':'B'})]:
   changed=copy.deepcopy(b);changed[part][key]=value
   with self.assertRaises(ValueError):restoration(a,changed)
 def test_validator_receipt_and_independent_id_guards(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);receipt=root/'receipt.json'
   for doc in [{},{'files':{}},{'files':[]},{'files':{'bad':{}}}]:
    receipt.write_text(json.dumps(doc))
    with self.assertRaises(ValueError):verify_validator_root(root,receipt)
   files={str(i):{'bytes':0,'sha256':'0'*64} for i in range(311)};receipt.write_text(json.dumps({'files':files}))
   with self.assertRaisesRegex(ValueError,'receipt identity'):verify_validator_root(root,receipt)
   files['../bad']=files.pop('0');receipt.write_text(json.dumps({'files':files}))
   with self.assertRaisesRegex(ValueError,'safe relative'):verify_validator_root(root,receipt)
  for value in [None,'','../x','a'*65]:
   with self.assertRaises(ValueError):expected_id(value)
if __name__=='__main__':unittest.main()
