"""Offline receipt verification. Actual pixel inspection remains a separate observation."""
import hashlib
import json
import re
import struct
import zlib
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / 'evidence'

def png_info(data):
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature'
    offset = 8
    compressed = b''
    ihdr = None
    ended = False
    while offset < len(data):
        size = int.from_bytes(data[offset:offset+4], 'big')
        assert size <= len(data) - offset - 12, 'PNG chunk bounds'
        kind = data[offset+4:offset+8]
        payload = data[offset+8:offset+8+size]
        crc = int.from_bytes(data[offset+8+size:offset+12+size], 'big')
        assert zlib.crc32(kind+payload) & 0xffffffff == crc, 'PNG CRC'
        if kind == b'IHDR':
            assert ihdr is None and offset == 8 and size == 13, 'PNG IHDR'
            ihdr = struct.unpack('>IIBBBBB', payload)
        elif kind == b'IDAT':
            compressed += payload
        elif kind == b'IEND':
            assert size == 0 and offset+12 == len(data), 'PNG IEND'
            ended = True
        offset += size+12
    assert ended and ihdr is not None, 'PNG end/header'
    width,height,depth,color,compression,filtering,interlace=ihdr
    assert (width,height,depth,color,compression,filtering,interlace)==(1280,720,8,2,0,0,0), 'actual RGB1280x720'
    decoder=zlib.decompressobj()
    pixels=decoder.decompress(compressed, (width*3+1)*height+1)
    assert decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, 'PNG compressed stream'
    assert len(pixels)==(width*3+1)*height, 'PNG decoded scanlines'
    assert all(pixels[row*(width*3+1)] <= 4 for row in range(height)), 'PNG filter types'
    return {'width':width,'height':height,'bitDepth':depth,'colorType':color,'decodedScanlineBytes':len(pixels),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}

def raw_text(path):
    raw=json.loads(path.read_text())
    return '\n'.join(item.get('text','') for item in raw['output']['payload']['output'])

def verify():
    sources=json.loads((EVIDENCE/'source-context.json').read_text())
    assert len(sources['source_checks'])==32 and all(v['matches'] and v['sha256']==v['expected'] for v in sources['source_checks'].values())
    assert sources['artifacts']['dist/web/nvwa_studio_bg.wasm']['sha256']=='d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8'
    network=[json.loads(line) for line in (EVIDENCE/'network.jsonl').read_text().splitlines()]
    for case in ('case-1','case-2'):
        for url,artifact in [('nvwa_studio.js','dist/web/nvwa_studio.js'),('nvwa_studio_bg.wasm','dist/web/nvwa_studio_bg.wasm'),('assets/fixtures/nvwa-humanoid.glb','dist/web/assets/fixtures/nvwa-humanoid.glb'),('works/character-loop.nvwa.json','docs/evidence/bounded-perf-20261013/common/character-loop.nvwa.json')]:
            matches=[row for row in network if row['path']==f'/{case}/{url}']
            assert len(matches)==1 and matches[0]['status']==200
            assert all(matches[0][k]==sources['artifacts'][artifact][k] for k in ('bytes','sha256'))
        runtime=json.loads((EVIDENCE/(case+'-runtime-event.json')).read_text())['event']
        assert runtime['capture_callback'] and runtime['capture_file_bytes']==0 and runtime['clock']=='bevy_TimeReal_since_first_update'
        assert runtime['clip']=='idle' and runtime['document_revision']==0 and runtime['ready']
    assert {row['path'] for row in network if row['status']!=200}=={'/favicon.ico','/case-1/assets/fixtures/nvwa-humanoid.glb.meta','/case-2/assets/fixtures/nvwa-humanoid.glb.meta'}
    result={}
    for case,file,wait in [('case-1','case-1-explicit.png','case-1-explicit-wait.raw.json'),('case-2','case-2-auto.png','case-2-auto-wait.raw.json')]:
        info=png_info((EVIDENCE/file).read_bytes())
        receipt=json.loads((EVIDENCE/(case+'-file.json')).read_text())
        assert all(info[k]==receipt[k] for k in ('bytes','sha256','width','height','bitDepth','colorType'))
        assert receipt['copySHA256']==info['sha256']
        text=raw_text(EVIDENCE/wait)
        assert "status: 'event-and-path'" in text and receipt['path'] in text
        start=re.search(r"waitStartUTC: '([^']+)'",text).group(1)
        end=re.search(r"finishedUTC: '([^']+)'",text).group(1)
        assert datetime.fromisoformat(start)<=datetime.fromisoformat(receipt['birthUTC'])<=datetime.fromisoformat(end)
        assert datetime.fromisoformat(start)<=datetime.fromisoformat(receipt['mtimeUTC'])<=datetime.fromisoformat(end)
        result[case]=info
    first=raw_text(EVIDENCE/'case-1-auto-wait.raw.json')
    assert "status: 'bounded-non-observation'" in first and '30000ms' in first
    cleanup=json.loads((EVIDENCE/'cleanup.json').read_text())
    assert cleanup['loads']==2 and cleanup['automaticTriggers']+cleanup['explicitTriggers']==3
    assert cleanup['portListenerAbsent'] and cleanup['processesAbsent'] and cleanup['remainingTabs']==[] and cleanup['viewport']=='reset'
    manifest=json.loads((EVIDENCE/'manifest.json').read_text())
    for name,expected in manifest.items():
        assert hashlib.sha256((EVIDENCE/name).read_bytes()).hexdigest()==expected, f'evidence hash: {name}'
    return result

if __name__=='__main__':
    print(json.dumps({'status':'VERIFIED bounded packet','actualPNGs':verify(),'limit':'Visual pixel inspection attributed separately; cause remains INCONCLUSIVE'},indent=2))
