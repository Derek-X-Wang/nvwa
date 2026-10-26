"""Bounded fourteen-triple runner and observed rest/pose consistency checks."""
import json
from pathlib import Path
from validate import validate, hashes, require
from contract import cases, load_capture

def witness(record):
    f=record['frame'];base=f['full_base'];body=next(p for p in base['parts'] if p['name']=='body')
    return {'body_rest':hashes.mesh_array_sha256(body['rest_positions']),
            'body_source_ids':hashes.mesh_array_sha256(body['source_ids'],integer=True),
            'body_pose':hashes.mesh_array_sha256(body['positions']),
            'bone_skin':hashes.mesh_array_sha256([b['skin'] for b in base['bones']]),
            'bone_names':[b['name'] for b in base['bones']]}

def check_matrix(observed):
    expected={(case,seconds) for case,spec in cases().items() for seconds in spec['samples_seconds']}
    require(set(observed)==expected,'exact seven cases by two held samples required')
    for case in cases():
        zero,two=observed[case,0],observed[case,2]
        require(zero['body_rest']==two['body_rest'] and zero['body_source_ids']==two['body_source_ids'],'same Work changed rest cage across held samples')
        require(zero['bone_names']==two['bone_names'],'named bone binding changed across held samples')
        require(zero['bone_skin']!=two['bone_skin'] and zero['body_pose']!=two['body_pose'],'observed source0/source2 pose movement missing')
    for recipe in ['default','minus','plus']:
        require(observed[recipe+'-arms',0]['body_rest']==observed[recipe+'-knee',0]['body_rest'],'same body recipe changed rest cage across clips')
    rests=[observed[case,0]['body_rest'] for case in ['default-arms','minus-arms','plus-arms','head-width-plus']]
    require(len(set(rests))==4,'distinct selected body recipes reused a rest cage')
    return {'result':'PASS','coverage':'observed body rest and body/bone pose changes at fourteen held samples only; no independent body reconstruction,112 bypass or between-frame claim'}

def run_manifest(path):
    path=Path(path);entries=json.loads(path.read_text());require(isinstance(entries,list) and len(entries)==14,'fourteen explicit raw-record triples required')
    observed={};reports=[]
    for entry in entries:
        key=(entry['case'],entry['seconds']);require(key not in observed,'duplicate cohort case/sample')
        require(len(entry['records'])==3,'exact A/B/A record paths required')
        records=[load_capture(path.parent/item['path'],path.parent/item['manifest']) for item in entry['records']]
        reports.append(validate(records,*key));observed[key]=witness(records[0])
    return {'result':'PASS','triples':reports,'matrix':check_matrix(observed),
            'limits':'42 held records only; four playing observations/witnesses and visible fit require separate root readback; no formal identity or CLI acceptance'}

if __name__=='__main__':
    import sys
    print(json.dumps(run_manifest(sys.argv[1]),indent=2))
