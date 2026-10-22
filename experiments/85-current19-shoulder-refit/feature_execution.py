"""Distinct feature-v4 admission; original capture and v3 policy remain immutable."""
from dataclasses import dataclass
from pathlib import Path
import re
import current19 as c
import provenance as p
from geometry_checks import Baseline,e
import feature_policy as feature

KIND='nvwa85-current19-feature-author-score-freeze-v4'
CANDIDATE_ID='nvwa-current19-shoulder-feature-refit-v4'
AUTHORING='FROZEN_FOR_CURRENT19_FEATURE_AUTHORING_V4'
SCORING='FROZEN_FOR_CURRENT19_FEATURE_SCORING_V4'
REFERENCE_POLICY_PATH=c.ROOT/'experiments/84-shoulder-rest-refit/geometry-policy.json'
REFERENCE_POLICY_SHA='864df1a9956712dda02942fdc3a5a099a8c1d789ab91776a648258d268cafc53'
SUPPORT_PATH=c.ROOT/'experiments/84-shoulder-rest-refit/authoring/support-proposal.json'
SUPPORT_SHA='66dd2cc157b92bf5651e3c1e88c33d3ce72e6f6ec9fed8694a27984970b05053'

FEATURE_POLICY_PATH=c.HERE/'feature-policy-v4.json'
SPEC_PATH=c.HERE/'FEATURE-POLICY-V4.md'
PREVIOUS_REJECTION_BYTES=2146411
PREVIOUS_REJECTION_SHA='10c8394cdb980d347a3c8bfbf0c034b858efdbf6bd13ba7750b804192759fd99'
PREVIOUS_SUMMARY_PATH=c.HERE/'evidence/authoring-rejection.json'
PREVIOUS_SUMMARY_SHA='0dbf0b35cae4f931218f85f2467d0ace15d4bdfa49bf3878416a7102785136dd'
NEW_FILES=('feature_execution.py','feature_evaluate.py','feature_author.py','feature_policy.py',
           'test_feature_execution.py','test_feature_evaluate.py','test_feature_author.py',
           'test_feature_policy.py','feature-policy-v4.json','FEATURE-POLICY-V4.md')


@dataclass
class Context:
    freeze: dict
    records: list
    loaded: list
    baseline: list
    mapping: dict
    policy: dict
    support: dict
    feature_policy: dict


def required_execution_paths():
    """Complete prospective source closure, separate from the old capture closure."""
    paths=set(p.capture_paths())
    paths.update(path.relative_to(c.ROOT).as_posix() for path in c.HERE.rglob('*.py'))
    paths.update(path.relative_to(c.ROOT).as_posix() for path in
                 (REFERENCE_POLICY_PATH,SUPPORT_PATH,c.HERE/'evidence/authoring-rejection.json'))
    paths.update((c.HERE/name).relative_to(c.ROOT).as_posix() for name in NEW_FILES)
    return sorted(paths)


def execution_files():
    return p.rows_for(c.ROOT,required_execution_paths())


def reference_policy():
    c.need(c.digest(REFERENCE_POLICY_PATH.read_bytes())==REFERENCE_POLICY_SHA,
           'immutable reference geometry policy differs')
    c.need(c.digest(SUPPORT_PATH.read_bytes())==SUPPORT_SHA,'immutable reference support differs')
    policy=c.strict_load(REFERENCE_POLICY_PATH.read_bytes())
    support=c.strict_load(SUPPORT_PATH.read_bytes())
    c.need(policy['authoring_policy_version']==3 and policy['candidate_count']==1 and
           policy['thresholds']==e.THRESHOLDS and policy['baseline_rest_bound_m']==1e-7 and
           policy['baseline_posed_bound_m']==1e-5,'original geometry policy invariants differ')
    for key in ('position_source_ids','incident_triangles0','normal_source_ids','normal_accumulation_triangles0'):
        c.need(policy[key]==support[key],'reference policy/support differ: '+key)
    # Old policy's hybrid metadata is historical. New cohort identity lives ONLY
    # in the stage freeze and new author/candidate/evaluation receipts.
    return policy,support


def feature_policy():
    policy=c.strict_load(FEATURE_POLICY_PATH.read_bytes())
    feature.validate_policy(policy)
    return policy


def verify_previous_rejection(row):
    """Bind the consumed v3 attempt itself, never a replacement summary."""
    c.need(type(row) is dict and set(row)=={'path','bytes','sha256'} and
           type(row['path']) is str and
           type(row['bytes']) is int and row['bytes']==PREVIOUS_REJECTION_BYTES and
           row['sha256']==PREVIOUS_REJECTION_SHA,'previous consumed-v3 rejection binding differs')
    summary_raw=PREVIOUS_SUMMARY_PATH.read_bytes()
    c.need(c.digest(summary_raw)==PREVIOUS_SUMMARY_SHA,'original v3 rejection summary differs')
    summary=c.strict_load(summary_raw)
    c.need(summary['authoring_receipt_sha256']==row['sha256'],
           'previous rejection/summary crosslink differs')
    path=Path(row['path'])
    c.need(path.is_absolute() and path==path.resolve() and path.is_file(),
           'previous consumed-v3 rejection path invalid')
    raw=path.read_bytes()
    c.need(len(raw)==row['bytes'] and c.digest(raw)==row['sha256'],
           'previous consumed-v3 rejection bytes differ')
    receipt=c.strict_load(raw)
    c.need(type(receipt['schema_version']) is int and receipt['schema_version']==1 and
           receipt['kind']=='nvwa85-current19-authoring-receipt-v1' and
           receipt['status']=='REJECT_AUTHORING_SINGLE_ATTEMPT' and
           receipt['candidate_id']=='nvwa-current19-shoulder-rest-refit-v1' and
           receipt['cohort_kind']==c.KIND and receipt['candidate_created'] is False and
           type(receipt['candidate_count']) is int and receipt['candidate_count']==1 and
           receipt['scoring']=='NOT-RUN','previous consumed-v3 rejection identity differs')
    for key in ('cohort_manifest_sha256','source_inventory_sha256','execution_files_sha256'):
        c.need(receipt[key]==summary[key],'previous rejection provenance differs: '+key)
    return receipt


def verify_freeze(freeze_path,allowed_statuses):
    c.need(freeze_path.is_file(),'parent current19 stage freeze required')
    freeze=c.strict_load(freeze_path.read_bytes())
    c.need(type(freeze['schema_version']) is int and freeze['schema_version']==1 and
           freeze['kind']==KIND and freeze['status'] in allowed_statuses,
           'wrong current19 stage authorization')
    c.need(freeze['cohort_kind']==c.KIND and freeze['candidate_id']==CANDIDATE_ID and
           type(freeze['candidate_count']) is int and freeze['candidate_count']==1,
           'wrong cohort or single candidate identity')
    for key in ('cohort_manifest_sha256','source_inventory_sha256','execution_files_sha256',
                'baseline_geometry_sha256'):
        c.need(type(freeze[key]) is str and re.fullmatch('[0-9a-f]{64}',freeze[key]),
               'missing/malformed stage hash: '+key)
    c.need(type(freeze['authoring_policy_version']) is int and
           freeze['authoring_policy_version']==4,'feature authoring policy version differs')
    c.need(type(freeze['feature_policy_sha256']) is str and
           re.fullmatch('[0-9a-f]{64}',freeze['feature_policy_sha256']) and
           c.digest(FEATURE_POLICY_PATH.read_bytes())==freeze['feature_policy_sha256'],
           'feature policy bytes differ')
    feature_policy()
    verify_previous_rejection(freeze['previous_rejection'])
    c.need(freeze['reference_policy_sha256']==REFERENCE_POLICY_SHA and
           freeze['support_sha256']==SUPPORT_SHA,'stage reference policy/support differs')
    rows=freeze['execution_files']
    p.check_rows(rows)
    c.need([row['path'] for row in rows]==required_execution_paths(),
           'full author/score execution closure incomplete/extra')
    c.need(p.inventory_digest(rows)==freeze['execution_files_sha256'],
           'author/score execution closure digest differs')
    attempt=Path(freeze['attempt_directory'])
    c.need(type(freeze['attempt_directory']) is str and attempt.is_absolute() and
           attempt==attempt.resolve(),'exact absolute parent attempt directory required')
    reference_policy()
    return freeze


def authenticate_current(corpus,freeze):
    """Authenticate actualV2 current19; independently rerun every baseline gate."""
    records=p.authenticate(corpus,freeze['cohort_manifest_sha256'],freeze['source_inventory_sha256'])
    c.need(c.digest((corpus/'geometry-audit.json').read_bytes())==freeze['baseline_geometry_sha256'],
           'frozen all19 baseline geometry audit differs')
    row=freeze['independent_audit']
    c.need(type(row) is dict and set(row)=={'path','bytes','sha256'},'independent baseline audit binding missing')
    path=Path(row['path'])
    c.need(type(row['path']) is str and path.is_absolute() and path==path.resolve() and path.is_file(),
           'independent baseline audit path invalid')
    raw=path.read_bytes()
    c.need(type(row['bytes']) is int and len(raw)==row['bytes'] and c.digest(raw)==row['sha256'],
           'independent baseline audit bytes differ')
    audit=c.strict_load(raw)
    c.need(audit['status']=='PASS_INDEPENDENT_CURRENT19_DATA_AUDIT' and audit['all19_complete'] is True and
           audit['candidate_read'] is False and audit['quality_acceptance'] is False and
           audit['manifest_sha256']==freeze['cohort_manifest_sha256'] and
           audit['run_id']==records[0]['run_id'] and
           [r['case'] for r in audit['results']]==list(c.CASES) and
           all(r['status']=='PASS' for r in audit['results']),
           'independent actual19 audit not admitted')
    provenance=audit['production_raw_provenance_admission_rerun']
    c.need(provenance['status']=='PASS' and provenance['records']==19 and
           provenance['manifest_sha256']==freeze['cohort_manifest_sha256'] and
           provenance['source_inventory_sha256']==freeze['source_inventory_sha256'],
           'independent current19 provenance crosslink differs')
    validator=Baseline();report=c.audit_geometry(records,validator)
    c.need(report['status']=='PASS_CURRENT19_GEOMETRY' and not report['failures'] and
           [row['case'] for row in report['results']]==list(c.CASES) and
           all(row['status']=='PASS' for row in report['results']),
           'fresh all19 baseline preflight failed')
    return records,report['results'],validator.mapping


def load_context(freeze_path,corpus,allowed_statuses):
    freeze=verify_freeze(freeze_path,allowed_statuses)
    records,baseline,mapping=authenticate_current(corpus,freeze)
    policy,support=reference_policy()
    return Context(freeze=freeze,records=records,
                   loaded=[(record['case'],record['snapshot']) for record in records],
                   baseline=baseline,mapping=mapping,policy=policy,support=support,
                   feature_policy=feature_policy())
