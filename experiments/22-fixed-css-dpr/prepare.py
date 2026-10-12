"""Stage exact dist/web runtime with a disclosed fixed-CSS geometry wrapper."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare(output, layout='fixed'):
    source = ROOT / 'dist/web'
    allowed = ROOT / '.work/bounded-scale-ime/issue3'
    output = output.resolve()
    if not output.is_relative_to(allowed) or output == allowed:
        raise ValueError(f'output must be a subdirectory of {allowed}')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('refusing to replace nonempty/non-directory output')
    html = (source / 'index.html').read_text()
    canvas = '<canvas id="nvwa" aria-label="Nvwa 3D character editor" tabindex="0"></canvas>'
    if html.count(canvas) != 1 or html.count('</head>') != 1 or html.count('</body>') != 1:
        raise ValueError('production HTML shape changed; review the wrapper contract')
    inputs = {str(path.relative_to(source)): sha(path) for path in sorted(source.rglob('*')) if path.is_file()}
    manifest = {
        'schema': 'nvwa-fixed-css-package-v1', 'productionInputs': inputs,
        'observerFiles': {'fixed-css-collector.js': sha(HERE / 'collector.js')},
        'runtime': 'exact existing dist/web JS/Wasm/assets via symlinks; no rebuild',
        'layout': layout,
        'geometryChange': ('production #nvwa reparented into static top-left CSS1100x640 parent; canvas retains100% CSS'
                           if layout=='fixed' else 'production body parent and canvas geometry unchanged'),
        'exportEffect': 'user-activated button outside canvas at CSS left1110/top0; changes focus after tested interval',
        'dprOverrides': False, 'rustChanges': False
    }
    location = 'left:1110px;top:0' if layout=='fixed' else 'right:0;bottom:0'
    stop_location = 'left:1110px;top:50px' if layout=='fixed' else 'right:0;bottom:50px'
    style = '<style>#nvwa-fixed-parent{width:1100px;height:640px;margin:0;padding:0;border:0}'+\
        '#nvwa-fixed-css-export{position:absolute;'+location+';width:90px;z-index:2}'+\
        '#nvwa-fixed-css-stop{position:absolute;'+stop_location+';width:90px;z-index:2}</style>'
    html = html.replace('</head>', style + '</head>')
    if layout=='fixed':
        html=html.replace(canvas,'<div id="nvwa-fixed-parent">' + canvas + '</div>')
    else:
        manifest['exportEffect']='user export/stop buttons overlay bottom-right90px normal canvas; focus changes after tested interval'
    # Escape script terminators even if an unexpected package filename contains them.
    metadata = json.dumps(manifest).replace('<', '\\u003c')
    html = html.replace('</body>', '<button id="nvwa-fixed-css-export">Export scale capture</button>'+
        '<button id="nvwa-fixed-css-stop">Stop and export</button>'+
        '<script type="application/json" id="nvwa-fixed-css-source">'+metadata+'</script>'+
        '<script src="fixed-css-collector.js"></script></body>')
    output.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        if child.name not in ('index.html', 'index.html.gz'):
            (output / child.name).symlink_to(child, target_is_directory=child.is_dir())
    (output / 'index.html').write_text(html)
    (output / 'fixed-css-collector.js').write_bytes((HERE / 'collector.js').read_bytes())
    # The embedded manifest avoids a circular wrapper hash. The sidecar pins it.
    manifest_path = output / 'probe-package.json'
    manifest_path.write_text(json.dumps({'source': manifest, 'wrapperSha256': sha(output / 'index.html')}, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'manifest': str(manifest_path),
        'wrapperSha256': sha(output / 'index.html'), 'source': manifest}, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--layout', choices=('normal','fixed'), default='fixed')
    args = parser.parse_args()
    try:
        prepare(args.output,args.layout)
    except (ValueError, OSError) as error:
        parser.error(str(error))
