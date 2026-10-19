"""Reauthenticate retained local archive and exact selected source bytes; no network."""
import argparse,hashlib,json,zipfile
from pathlib import Path
EXP=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def check(ok,msg):
 if not ok:raise ValueError(msg)
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True,type=Path);a=p.parse_args();r=json.loads((EXP/'SOURCE.json').read_text());raw=a.archive.read_bytes();check(len(raw)==r['archive']['bytes'] and sha(raw)==r['archive']['sha256'],'whole archive identity mismatch')
 with zipfile.ZipFile(a.archive) as z:
  for name,item in r['files'].items():
   b=z.read(item['archive_member']);check(len(b)==item['bytes'] and sha(b)==item['sha256'],'selected original member mismatch');check(b==(EXP/'source'/name).read_bytes(),'retained original subset changed');check(f"{z.getinfo(item['archive_member']).CRC:08x}"==item['zip_crc'],'selected CRC mismatch')
  metadata=z.read('packs/makehuman_system_assets.json');check(metadata==(EXP/'source/provenance/pack.json').read_bytes(),'pack provenance changed')
 print(json.dumps({'archive_identity':r['archive'],'selected_original_bytes':r['subset_bytes'],'selected_members':len(r['files']),'selected_crc':'PASS','network_bytes':0,'scope':'bounded selected-member verification only; not all-member CRC or asset admission'},indent=2))
if __name__=='__main__':main()
