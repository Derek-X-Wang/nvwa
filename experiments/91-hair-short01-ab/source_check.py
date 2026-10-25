"""Short01 identity/count plumbing around the unchanged retained scalar replay."""
import hashlib
import json
from pathlib import Path
import cpu_replay as numeric

EXP = Path(__file__).resolve().parent
ROOT = EXP.parents[1]
SHA = lambda raw: hashlib.sha256(raw).hexdigest()
A_HASHES = {'short04.mhclo':'d60640aa4c4ffce1aa269647ba436b6ee0bb21bb948f927b84e27a48d2107157',
            'short04.obj':'676964a133ee35ffcea1195382bf75542da7a298931e4001bc7b0d7b707225de',
            'short04.mhmat':'7a3ac74db8478aa0afdb8a596c6fe3997d1a8a09d12211d70e8f1e9f0b7e0e97'}
B_HASHES = {'short01.mhclo':'ae1ffaa98da5753b803b3a173bede4895d2215e6bb94763f3765a71f0e984f35',
            'short01.obj':'d998d8416f9b5d5591f1d756f4d292288d000a6951bc0f4d2e8e72727bbc44fa',
            'short01.mhmat':'01e2e12ce3f3d3c859225456660acadcdd27d4f4b4d888bcbd6f11998cadd975',
            'short01_diffuse.png':'f34a0957184e3d1e911ed59245f874f8d4843f61ee44ff49f43edb4be0196949',
            'makehuman_system_assets.json':'e86f1572432cfd062f372adddba4eb7c2e2e31280e96c29291a970320e0a5df0'}
RGBA = {'a':'c7ba27fdb3c6c3872f9e0c2c1ddc1b7f042d9fe8211ad0034d1dcb0e5d030bdb',
        'b':'aeda8adafdfb7dc9259c074c1b1f9cb053e7d7add625abb909b00f9416606148'}

def source(which):
    numeric.require(which in ('a','b'), 'exact asset selector required')
    stem = (ROOT/'assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04') if which=='a' else EXP/'candidate/short01/short01'
    expected = A_HASHES if which=='a' else B_HASHES
    for name, digest in expected.items():
        numeric.require(SHA((stem.parent/name).read_bytes()) == digest, 'source authentication failed '+name)
    obj = numeric.mesh(stem.with_suffix('.obj').read_text())
    expected_counts = (865,991,1050) if which=='a' else (2984,3177,3678)
    numeric.require((obj['count'],len(obj['pairs']),len(obj['indices'])//3)==expected_counts, 'asset count differs')
    rows,scales=numeric.mapping(stem.with_suffix('.mhclo').read_text(),obj['count'])
    return obj,rows,scales

# Reuse the original replay arithmetic byte-for-byte. Its existing per-asset
# source seam selects these authenticated files rather than the old same-asset B.
numeric.source=source

def replay(base,which,**controls):
    result=numeric.replay(base,which,**controls)
    obj,_,_=source(which)
    normals=[[0.,0.,0.] for _ in result['rest']]
    for k in range(0,len(obj['indices']),3):
        ids=[obj['pairs'][obj['indices'][k+j]][0] for j in range(3)]
        a,b,c=[result['rest'][i] for i in ids]
        n=numeric.cross(numeric.sub(b,a),numeric.sub(c,a))
        for i in ids:normals[i]=[x+y for x,y in zip(normals[i],n)]
    result['rest_normals']=[numeric.unit(n) for n in normals]
    return result
