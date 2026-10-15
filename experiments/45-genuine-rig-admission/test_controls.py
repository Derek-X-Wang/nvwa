#!/usr/bin/env python3
"""Bounded controls for the report study; no models, build or export."""
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parent
study_path=HERE/'probe.py'
study={'__file__':str(study_path),'__name__':'study_controls'}
exec(compile(study_path.read_bytes(),str(study_path),'exec'),study)


FLOAT_ATOL=1e-13
FLOAT_RTOL=1e-13


def compare_historical(actual, expected, path='$', stats=None):
    """Exact JSON structure/types; only finite float leaves use a tolerance."""
    check=study['require']
    check(type(actual) is type(expected), 'comparison type mismatch: '+path)
    if type(expected) is dict:
        check(all(type(key) is str for key in actual) and
              all(type(key) is str for key in expected), 'comparison key type: '+path)
        check(actual.keys()==expected.keys(), 'comparison dictionary keys: '+path)
        for key in expected:
            compare_historical(actual[key],expected[key],path+'.'+key,stats)
    elif type(expected) is list:
        check(len(actual)==len(expected), 'comparison list shape: '+path)
        for index,(left,right) in enumerate(zip(actual,expected)):
            compare_historical(left,right,path+'['+str(index)+']',stats)
    elif type(expected) is float:
        check(math.isfinite(actual) and math.isfinite(expected),
              'comparison nonfinite float: '+path)
        difference=abs(actual-expected)
        tolerance=FLOAT_ATOL+FLOAT_RTOL*max(abs(actual),abs(expected))
        check(difference<=tolerance, 'comparison numeric drift: '+path)
        if stats is not None:
            stats['float_leaves']+=1
            stats['changed_float_leaves']+=actual!=expected
            stats['max_absolute_difference']=max(stats['max_absolute_difference'],difference)
    else:
        check(type(expected) in (str,int,bool,type(None)),
              'comparison unsupported type: '+path)
        check(actual==expected, 'comparison exact value: '+path)


def main():
    check=study['require']
    rejected={}

    def rejects(name, function, text):
        try:
            function()
        except ValueError as error:
            check(text in str(error), 'wrong rejection: '+name)
            rejected[name]=str(error)
        else:
            raise ValueError('control unexpectedly accepted: '+name)

    root=study['ROOT']
    before={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in study['PINNED']}
    actual=study['inspect']()
    for name,pin in study['PINNED'].items():
        data=(root/name).read_bytes()
        changed=bytes([data[0]^1])+data[1:]
        rejects('wrong_hash:'+name,
                lambda:study['check_hash'](changed,pin,name),'SHA256 mismatch')
    for key in ('old43_policy_hip_position_max_error_m',
                'subtract_unrotated_pelvis_offset_max_error_m',
                'add_target_root_rest_again_max_error_m'):
        rejects(key, lambda:study['check_root_oracle'](actual[key]),
                'target pelvis world trajectory mismatch')
    rejects('semantic_axes_from_equivariance',
            lambda:study['reject_semantic_axis_claim'](actual['all_signed_bases']),
            'semantic axes unresolved')
    bad=dict(actual['all_signed_bases'],improper=0)
    rejects('missing_improper_basis_controls',
            lambda:study['reject_semantic_axis_claim'](bad),'basis enumeration')

    # Keep original private proof bytes and compare the shared numeric values.
    historical={'probe.py':'eda8d227ff632cacf7701985de26b0df8a6b78a8426861c33e0a771b3b798058',
                'numeric-proof.json':'7ef382ef09efe79d9cbb0ae558943ec54c5a805323162a6df20ddf9a61665104',
                'PROOF-NOTES.md':'7ab0d8fbe50b78ea594de7a0258080e9abc9e6d06b6cdeccd4f8441f6b281a76'}
    for name,pin in historical.items():
        study['check_hash']((HERE/'historical'/name).read_bytes(),pin,'historical/'+name)
    old=json.loads((HERE/'historical/numeric-proof.json').read_bytes())
    shared=[key for key in old if key not in ('kind','raw_sha256','source_sha256')]
    comparison={'float_leaves':0,'changed_float_leaves':0,'max_absolute_difference':0.0}
    for key in shared:
        compare_historical(actual[key],old[key],key,comparison)

    # Exercise the actual recursive comparison seam. Runtime arithmetic may
    # change the last bit, but structure, identities and discrete types may not.
    last_bit=math.nextafter(1.0,2.0)
    compare_historical({'nested':[last_bit,2,True,'soma30',None]},
                       {'nested':[1.0,2,True,'soma30',None]})
    material=json.loads(json.dumps(actual['root']))
    material['min_xyz'][0]+=1e-6
    rejects('comparison_material_numeric_drift',
            lambda:compare_historical(material,actual['root']),'comparison numeric drift')
    fixture={'values':[1.0,2,True,'soma30',None]}
    typed_cases={
        'missing_key':({},fixture,'dictionary keys'),
        'extra_key':(dict(fixture,extra=0),fixture,'dictionary keys'),
        'list_length':({'values':[1.0]},fixture,'list shape'),
        'list_type':({'values':tuple(fixture['values'])},fixture,'type mismatch'),
        'integer_value':({'values':[1.0,3,True,'soma30',None]},fixture,'exact value'),
        'integer_as_float':({'values':[1.0,2.0,True,'soma30',None]},fixture,'type mismatch'),
        'boolean_as_integer':({'values':[1.0,2,1,'soma30',None]},fixture,'type mismatch'),
        'integer_as_boolean':({'values':[1.0,True,True,'soma30',None]},fixture,'type mismatch'),
        'identity_string':({'values':[1.0,2,True,'soma77',None]},fixture,'exact value'),
        'null_type':({'values':[1.0,2,True,'soma30','None']},fixture,'type mismatch'),
    }
    for name,(left,right,message) in typed_cases.items():
        rejects('comparison_'+name,lambda:compare_historical(left,right),message)
    for name,value in [('nan',math.nan),('positive_infinity',math.inf),
                       ('negative_infinity',-math.inf)]:
        rejects('comparison_actual_'+name,
                lambda:compare_historical({'nested':[value]},{'nested':[1.0]}),'nonfinite float')
    for name,value in [('nan',math.nan),('infinity',math.inf)]:
        rejects('comparison_expected_'+name,
                lambda:compare_historical({'nested':[1.0]},{'nested':[value]}),'nonfinite float')

    private=HERE/'.work'
    private.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='controls-',dir=private) as temporary:
        target=Path(temporary)/'result.json'
        good=study['encode'](actual)
        study['write_result'](target,good)
        study['write_result'](target,good)
        rejects('different_existing_output',
                lambda:study['write_result'](target,b'different'),'different output exists')
        check(target.read_bytes()==good, 'existing output changed')
        link=Path(temporary)/'link.json'
        link.symlink_to(target)
        rejects('output_symlink',lambda:study['write_result'](link,good),'output symlink')
    after={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
           for name in study['PINNED']}
    check(before==after, 'public inputs mutated')
    result={'result':'PASS numerical controls; admission remains HOLD',
            'probe_sha256':hashlib.sha256(study_path.read_bytes()).hexdigest(),
            'test_controls_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'rejections':rejected,'historical_files_unchanged_sha256':historical,
            'historical_shared_fields_match_with_float_tolerance':shared,
            'historical_float_comparison':dict(comparison,atol=FLOAT_ATOL,rtol=FLOAT_RTOL,
                policy='exact keys/shapes/types/discrete values; finite floats: abs(a-b)<=atol+rtol*max(abs(a),abs(b))'),
            'last_bit_acceptance_control':{'expected':1.0,'actual':last_bit,'accepted':True},
            'python_version':sys.version.split()[0],
            'public_input_hashes_before_and_after_equal':True,
            'temporary_resources_removed':True,
            'normalized_schema_export_playback':'NOT-RUN'}
    data=study['encode'](result)
    if len(sys.argv)==3 and sys.argv[1]=='--out':
        study['write_result'](Path(sys.argv[2]),data)
        print(json.dumps({'result':'PASS','rejected_controls':len(rejected),
                          'sha256':hashlib.sha256(data).hexdigest()}))
    elif len(sys.argv)==1:
        print(data.decode(),end='')
    else:
        raise ValueError('usage: test_controls.py [--out new-result.json]')


if __name__=='__main__':
    main()
