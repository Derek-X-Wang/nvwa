"""Content screening of pinned original documents; never assigns license policy.

A full-text candidate means recognizable operative text is present. It does not
establish legal completeness, applicability, authenticity or expression coverage.
"""
import hashlib,re
from pathlib import Path

CLASSIFICATION_VERSION=1
CODE_EXTENSIONS={'.rs','.c','.h','.cc','.cpp','.hpp','.py','.js','.ts','.tsx','.jsx','.go','.java','.swift','.kt','.m','.mm','.sh'}

def classify_document(path,data):
    text=data.decode('utf-8',errors='replace');flat=re.sub(r'\s+',' ',text.lower());name=Path(path).name.lower();signatures=[]
    checks={
      'permission-grant-and-warranty-text':('permission is hereby granted' in flat and ('software is provided' in flat or 'software are provided' in flat) and ('copyright' in flat or 'mit no attribution' in flat or 'permission notice' in flat)),
      'bsd-operative-conditions-and-warranty-text':all(s in flat for s in ['redistribution and use','software is provided','redistributions']),
      'isc-operative-permission-and-warranty-text':all(s in flat for s in ['permission to use, copy','software is provided','copyright']),
      'apache-numbered-license-text':all(s in flat for s in ['terms and conditions for use, reproduction, and distribution','1. definitions.','9. accepting warranty']),
      'unlicense-permission-and-warranty-text':all(s in flat for s in ['anyone is free to copy','software is provided','free and unencumbered software']),
      'zlib-operative-restrictions-and-warranty-text':all(s in flat for s in ['altered source versions','this notice may not be removed','provided']),
      'gpl-numbered-license-and-application-text':all(s in flat for s in ['gnu general public license','terms and conditions','how to apply these terms']),
      'cc0-waiver-fallback-and-limitations-text':all(s in flat for s in ['cc0 1.0 universal','2. waiver.','3. public license fallback.','4. limitations and disclaimers.']),
    }
    signatures=[k for k,v in checks.items() if v]
    if Path(path).suffix.lower() in CODE_EXTENSIONS:kind='source-code-not-license-document';full=False
    elif signatures:kind='full-license-text-candidate';full=True
    elif name.startswith('authors'):kind='authors-attribution';full=False
    elif name.startswith('attribution') or ('license:' in flat and 'credit:' in flat):kind='asset-or-source-attribution-notice';full=False
    elif len(flat)<1000 and ('dual-licensed' in flat or 'terms of either license' in flat or re.fullmatch(r'[a-z0-9.+()/ -]+',flat) and (' or ' in flat or ' and ' in flat) and len(flat)<100):kind='license-choice-notice';full=False
    elif 'licensed under' in flat or 'licensing of these crates' in flat or 'license' in flat and ('http' in flat or 'see [' in flat):kind='license-reference-or-provenance-notice';full=False
    elif 'copyright' in flat:kind='copyright-or-authorship-notice';full=False
    else:kind='unresolved-document';full=False
    return {'classification_version':CLASSIFICATION_VERSION,'kind':kind,'full_license_text_candidate':full,'content_signatures':signatures,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'scope':'content screening only; original bytes retained; legal/applicability/expression coverage NOT-RUN'}

def select_documents(paths):
    included=[];excluded=[]
    for path in paths:
        record=classify_document(path,path.read_bytes())
        (excluded if record['kind']=='source-code-not-license-document' else included).append((path,record))
    return included,excluded
