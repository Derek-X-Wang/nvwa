#!/usr/bin/env python3
"""Compare actual seven-key source/target directions and draw captured skeletons."""
import json
from pathlib import Path
import struct
import candidate as c
import evaluate as e

R=c.HERE/'results'

def bits(value):
    if isinstance(value,list):return [bits(v) for v in value]
    if isinstance(value,dict):return {k:bits(v) for k,v in value.items()}
    return ('float64',struct.pack('>d',value).hex()) if type(value) is float else (type(value).__name__,value)

def raw(variant,platform):return json.loads((R/(platform+'-'+variant+'.json')).read_text())

def globals_(sample):
    return {n['gltf_node_index']:e.E.from_column_major(n['global']) for n in sample['nodes'] if n['gltf_node_index'] is not None}

def measure():
    meta,frames,roots=e.source_frames();si={name:i for i,name in enumerate(meta['joint_names'])}
    result={'status':'PASS','quality':'HOLD','source':'independent retained source FK; actual captured target node origins/chest affine inverse','variants':{}}
    for variant in ['baseline','candidate']:
        pairs={p:raw(variant,p) for p in ['native','web']};samples=[];parity=True
        for platform,capture in pairs.items():
            e.D.validate_capture(capture,platform)
        c.need(len(pairs['native']['samples'])==len(pairs['web']['samples'])==len(e.KEYS), 'complete exact seven-key capture pair')
        for ns,ws in zip(pairs['native']['samples'],pairs['web']['samples']):
            key=ns['source_key_index'];c.need(key==ws['source_key_index'],'same runtime keys')
            sg,sp=e.D.fk(meta,frames[key],roots[key]);row={'key_index':key,'platforms':{}}
            by_platform={}
            for platform,sample in [('native',ns),('web',ws)]:
                gl=globals_(sample);arms={}
                for side,index,child in [('Left',7,6),('Right',4,3)]:
                    expected=e.D.norm(e.D.mv(e.D.tr(sg[si['Chest']]),e.D.sub(sp[si[side+'ForeArm']],sp[si[side+'Arm']])))
                    actual=e.direction(gl,index,child)
                    arms[side]={'source_chest_relative':expected,'actual_chest_relative':actual,'component_error':max(abs(x-y) for x,y in zip(expected,actual)),'angle_error_deg':e.D.angle(expected,actual)}
                    if variant=='candidate':c.need(arms[side]['component_error']<=2e-6 and arms[side]['angle_error_deg']<=.001,'actual runtime source direction gate')
                row['platforms'][platform]=arms
                by_platform[platform]={n['gltf_node_index']:{k:n[k] for k in ['translation','rotation','scale','global']} for n in sample['nodes'] if n['gltf_node_index'] is not None}
            parity=parity and bits(by_platform['native'])==bits(by_platform['web'])
            samples.append(row)
        c.need(parity,'actual native/Web typed bit-exact local TRS and global matrices')
        result['variants'][variant]={'native_web_node_TRS_global_binary64_bit_exact':parity,'samples':samples}
    (R/'runtime-directions.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def skeletons(platform):
    width,height=1540,560;parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#111821"/>','<style>text{font:14px system-ui;fill:#e4edf7}.small{font-size:11px;fill:#aab9c8}</style>',f'<text x="18" y="24">{platform}: actual captured skeletons, exact seven keys, fixed world projection</text>','<text x="18" y="44" class="small">Bodily left (.R) orange; bodily right (.L) cyan. One fixed orthographic x+0.35z / y-0.12z projection, 105px/m. No per-key fit.</text>']
    asset=e.E.Asset()
    for r,variant in enumerate(['baseline','candidate']):
        for col,sample in enumerate(raw(variant,platform)['samples']):
            x0=110+col*210;y0=290+r*245
            parts.append(f'<text x="{x0-80}" y="{y0-220}">{variant} · key {sample["source_key_index"]}</text>')
            gl=globals_(sample)
            def xy(i):
                x,y,z=e.points(gl,i);return x0+105*(x+.35*z),y0-105*(y-.12*z)
            for i in range(18):
                parent=asset.parents[i]
                if parent is None:continue
                a,b=xy(i),xy(parent);name=asset.nodes[i]['name'];color='#fbad55' if name.endswith('.R') else '#64d8ed' if name.endswith('.L') else '#c4d2df'
                parts.append(f'<line x1="{a[0]:.5f}" y1="{a[1]:.5f}" x2="{b[0]:.5f}" y2="{b[1]:.5f}" stroke="{color}" stroke-width="3"/>')
                parts.append(f'<circle cx="{a[0]:.5f}" cy="{a[1]:.5f}" r="2.5" fill="{color}"/>')
    parts.append('</svg>');(R/(platform+'-skeletons.svg')).write_text('\n'.join(parts)+'\n')

def skeletons_png(platform):
    # Optional CPU-only diagnostic drawing, not a screenshot or mesh rendering.
    from PIL import Image, ImageDraw
    image=Image.new('RGB',(1540,560),'#111821');draw=ImageDraw.Draw(image)
    draw.text((18,12),platform+': actual seven-key captured skeletons, fixed projection',fill='#e4edf7')
    draw.text((18,32),'Bodily left (.R) orange; bodily right (.L) cyan. Fixed world projection; 105px/m; no per-key fit.',fill='#aab9c8')
    asset=e.E.Asset()
    for row,variant in enumerate(['baseline','candidate']):
        for col,sample in enumerate(raw(variant,platform)['samples']):
            x0=110+col*210;y0=290+row*245
            draw.text((x0-80,y0-220),variant+' key '+str(sample['source_key_index']),fill='#e4edf7')
            gl=globals_(sample)
            def xy(i):
                x,y,z=e.points(gl,i);return x0+105*(x+.35*z),y0-105*(y-.12*z)
            for i in range(18):
                parent=asset.parents[i]
                if parent is None:continue
                a,b=xy(i),xy(parent);name=asset.nodes[i]['name'];color='#fbad55' if name.endswith('.R') else '#64d8ed' if name.endswith('.L') else '#c4d2df'
                draw.line([a,b],fill=color,width=3)
                draw.ellipse((a[0]-2.5,a[1]-2.5,a[0]+2.5,a[1]+2.5),fill=color)
    image.save(R/(platform+'-skeletons.png'))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--raster',action='store_true');args=parser.parse_args()
    result=measure()
    for platform in ['native','web']:
        skeletons(platform)
        if args.raster:skeletons_png(platform)
    print(json.dumps({'status':result['status'],'variants':{k:{'node_parity':v['native_web_node_TRS_global_binary64_bit_exact'],'keys':len(v['samples'])} for k,v in result['variants'].items()}}))
