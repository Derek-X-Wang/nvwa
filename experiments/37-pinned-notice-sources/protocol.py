"""Small Git-object and document-evidence helpers; no network or Cargo calls."""
import hashlib,json
from pathlib import PurePosixPath

def sha256(data):return hashlib.sha256(data).hexdigest()
def git_object(kind,data):return hashlib.sha1((kind+' '+str(len(data))+'\0').encode()+data).hexdigest()
def canonical(data):return json.dumps(data,sort_keys=True,separators=(',',':')).encode()
def safe_relative(path):
    p=PurePosixPath(path)
    return bool(path) and not p.is_absolute() and '..' not in p.parts and str(p)==path

def check_tree(tree):
    """Reconstruct every returned Git tree, including the root, from raw entries."""
    errors=[];nodes={}
    if tree.get('truncated') is not False:errors.append('truncated/unknown recursive tree')
    for node in tree.get('tree',[]):
        path=node.get('path','')
        if not safe_relative(path) or path in nodes:errors.append('unsafe or duplicate Git tree path');continue
        if node.get('type') not in {'blob','tree','commit'}:errors.append('unsupported Git object kind')
        if node.get('mode') not in {'100644','100755','120000','040000','160000'}:errors.append('unsupported Git tree mode')
        nodes[path]=node
    directories={'':tree.get('sha')}
    directories.update({p:n['sha'] for p,n in nodes.items() if n['type']=='tree'})
    for p in nodes:
        parent=str(PurePosixPath(p).parent);parent='' if parent=='.' else parent
        if parent not in directories:errors.append('missing Git parent tree: '+p)
    for directory,expected in directories.items():
        entries=[]
        for p,node in nodes.items():
            parent=str(PurePosixPath(p).parent);parent='' if parent=='.' else parent
            if parent==directory:entries.append((PurePosixPath(p).name,node))
        entries.sort(key=lambda x:(x[0]+('/' if x[1]['type']=='tree' else '')).encode())
        try:
            data=b''.join((format(int(n['mode'],8),'o')+' '+name+'\0').encode()+bytes.fromhex(n['sha']) for name,n in entries)
            if git_object('tree',data)!=expected:errors.append('reconstructed Git tree mismatch: '+(directory or '/'))
        except (ValueError,KeyError):errors.append('malformed Git tree object')
    return nodes,errors

def legal_ancestor_entries(nodes,package_path):
    p=PurePosixPath(package_path or '.');ancestors={str(p),*(str(x) for x in p.parents),'.'}
    return [n for path,n in nodes.items() if n['type']=='blob' and str(PurePosixPath(path).parent) in ancestors and PurePosixPath(path).name.upper().startswith(('LICENSE','LICENCE','COPYING'))]
