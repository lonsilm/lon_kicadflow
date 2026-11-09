#!/usr/bin/env python3
"""Portable, stdlib-only KiCad helpers. Python >= 3.10.

Read-only for existing engineering files. new-project only creates a new folder.
No editor saves, upgrades, IPC mutations, zone refills, or design restoration.
Run --help and each subcommand's --help for the explicit interface.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import locale
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
import zipfile

from sexpr_read import parse, quote


ENGINEERING = {'.kicad_pro', '.kicad_pcb', '.kicad_sch', '.kicad_dru',
               '.kicad_sym', '.kicad_mod', '.sch', '.lib', '.dcm', '.pretty'}
TABLES = {'sym-lib-table', 'fp-lib-table'}
SKIP = {'.git', '__pycache__', 'reports', 'manufacturing', 'archive',
        'backups', 'node_modules', '.venv', 'venv'}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat()


def sha(path):
    with Path(path).open('rb') as f:
        if sys.version_info >= (3, 11):
            return hashlib.file_digest(f, 'sha256').hexdigest()
        h = hashlib.sha256()
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
        return h.hexdigest()


def write_json(path, obj):
    path = Path(path).resolve()
    if path.suffix.lower() in ENGINEERING or path.name in TABLES:
        raise ValueError('Report output must not be an engineering source file')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def emit(obj, out=None):
    if out:
        write_json(out, obj)
        obj = {'output': str(Path(out).resolve()), 'report_fields': list(obj)}
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def decode(data):
    for enc in ('utf-8', locale.getpreferredencoding(False)):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode('utf-8', errors='replace')


def run(args, timeout=180):
    p = subprocess.run([str(a) for a in args], capture_output=True, timeout=timeout)
    return {'command': [str(a) for a in args], 'returncode': p.returncode,
            'stdout': decode(p.stdout), 'stderr': decode(p.stderr)}


def require_success(result):
    if result['returncode']:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def cli_candidates(explicit=None):
    vals = [explicit, os.environ.get('KICAD_CLI'), shutil.which('kicad-cli')]
    if os.name == 'nt':
        for var in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
            root = Path(os.environ.get(var, 'C:/__not_present__'))
            vals.extend(str(p) for p in sorted(root.glob('KiCad/*/bin/kicad-cli.exe'), reverse=True))
            vals.append(str(root / 'KiCad/bin/kicad-cli.exe'))
    elif sys.platform == 'darwin':
        vals.extend(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli',
                     '/Applications/KiCad/KiCad.app/Contents/Applications/kicad-cli'])
    else:
        vals.extend(['/usr/bin/kicad-cli', '/usr/local/bin/kicad-cli'])
    seen = set()
    for val in vals:
        if val and Path(val).is_file():
            p = Path(val).resolve()
            if str(p) not in seen:
                seen.add(str(p))
                yield p


def get_cli(explicit=None):
    if explicit and not Path(explicit).is_file():
        raise FileNotFoundError(f'Explicit CLI does not exist: {explicit}')
    errors = []
    for p in cli_candidates(explicit):
        try:
            result = require_success(run([p, 'version'], timeout=15))
            return p, result['stdout'].strip()
        except Exception as e:
            errors.append(str(e))
            if explicit:
                break
    raise RuntimeError('No usable kicad-cli. Pass --cli PATH or set KICAD_CLI. ' + '; '.join(errors))


def config_roots():
    paths = []
    for key in ('KICAD_CONFIG_HOME',):
        if os.environ.get(key):
            paths.append(Path(os.environ[key]))
    if os.name == 'nt':
        if os.environ.get('APPDATA'):
            paths.append(Path(os.environ['APPDATA']) / 'kicad')
    elif sys.platform == 'darwin':
        paths.append(Path.home() / 'Library/Preferences/kicad')
    else:
        paths.append(Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'kicad')
    return list(dict.fromkeys(p.resolve() for p in paths))


def probe(args):
    result = {'time': now(), 'platform': platform.platform(), 'python': sys.executable,
              'config_roots': [str(p) for p in config_roots()],
              'kicad_environment': {k: ('<redacted>' if re.search(r'TOKEN|SECRET|PASSWORD|API_KEY', k, re.I) else v)
                                    for k, v in os.environ.items() if k.startswith('KICAD')},
              'tools': []}
    for cli in cli_candidates(args.cli):
        row = {'cli': str(cli), 'version_result': run([cli, 'version'], timeout=15)}
        row['sibling_python_candidates'] = [str(p) for p in
            (cli.parent / 'python.exe', cli.parent / 'python3', cli.parent / 'python') if p.is_file()]
        row['resource_candidates'] = [str(p) for p in
            (cli.parent.parent / 'share/kicad', cli.parent.parent / 'Resources',
             Path('/usr/share/kicad')) if p.is_dir()]
        result['tools'].append(row)
    result['hotkey_files'] = [str(p) for root in config_roots() if root.is_dir()
                              for p in sorted(root.rglob('*.hotkeys'))]
    result['note'] = 'Detection only; no configuration, package installation, editor launch, or design changes.'
    emit(result, args.out)


def source_files(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.endswith('-backups')
                         and not (Path(current) / d).is_symlink())
        for name in sorted(files):
            p = Path(current) / name
            if p.is_symlink():
                continue
            if p.suffix.lower() in ENGINEERING or name in TABLES:
                yield p


def capture(root):
    root = Path(root).resolve()
    return {'time': now(), 'root': str(root),
            'scope': 'KiCad sources/libraries/tables, excluding generated report/archive/backup folders and symlinks; not a backup',
            'files': {str(p.relative_to(root)).replace('\\', '/'):
                      {'sha256': sha(p), 'bytes': p.stat().st_size} for p in source_files(root)}}


def diff_sources(before, after):
    a, b = before['files'], after['files']
    return {'added': sorted(b.keys() - a.keys()), 'removed': sorted(a.keys() - b.keys()),
            'changed': sorted(k for k in a.keys() & b.keys() if a[k]['sha256'] != b[k]['sha256'])}


def snapshot(args):
    emit(capture(args.project), args.out)


def compare(args):
    before = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    after = capture(args.project or before['root'])
    result = diff_sources(before, after)
    result.update(time=now(), unchanged=not any(result.values()), compared_files=len(after['files']))
    emit(result, args.out)
    return 0 if result['unchanged'] else 2


def read_board(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    root = parse(data.decode('utf-8-sig'))
    if root.tag != 'kicad_pcb':
        raise ValueError('Expected a modern .kicad_pcb S-expression')
    layers = root.first('layers')
    copper = [n.atom() for n in layers.children[1:] if n.atom() and n.atom().endswith('.Cu')]
    def order(name):
        return 0 if name == 'F.Cu' else 1000 if name == 'B.Cu' else int(re.search(r'\d+', name).group())
    copper.sort(key=order)
    return path, data, root, copper


def inspect_board(args):
    path, data, root, copper = read_board(args.board)
    setup = root.first('setup')
    general = root.first('general')
    fps = []
    models = []
    pad_count = 0
    for f in root.named('footprint'):
        props = {p.atom(): p.atom(2) for p in f.named('property')}
        for t in f.named('fp_text'):
            if t.atom() in ('reference', 'value'):
                props.setdefault(t.atom().capitalize(), t.atom(2))
        pads = f.named('pad')
        pad_count += len(pads)
        row = {'reference': props.get('Reference'), 'value': props.get('Value'),
               'footprint': f.atom(), 'layer': f.first('layer').atom() if f.first('layer') else None,
               'at_mm_deg': [x.value for x in f.first('at').children[1:]] if f.first('at') else None,
               'pad_count': len(pads)}
        if args.detail:
            row['pads'] = [{'number': p.atom(), 'type': p.atom(2),
                'net': p.first('net').atom(2) if p.first('net') else '',
                'at_local': [x.value for x in p.first('at').children[1:]] if p.first('at') else None}
                for p in pads]
        fps.append(row)
        models.extend({'reference': row['reference'], 'path': m.atom()} for m in f.named('model'))
    result = {'source': str(path), 'time': now(), 'sha256': hashlib.sha256(data).hexdigest(),
              'file_version': root.first('version').atom(), 'copper_layers': copper,
              'copper_layer_count': len(copper),
              'thickness_mm': general.first('thickness').atom() if general and general.first('thickness') else None,
              'counts': {'footprints': len(fps), 'pads': pad_count, 'segments': len(root.named('segment')),
                         'track_arcs': len(root.named('arc')), 'vias': len(root.named('via')),
                         'zones': len(root.named('zone')),
                         'edge_shapes': sum(1 for n in root.children if n.tag and n.tag.startswith('gr_')
                                            and n.first('layer') and n.first('layer').atom() == 'Edge.Cuts')},
              'saved_zone_fill_blocks': sum(len(z.named('filled_polygon')) for z in root.named('zone')),
              'footprints': fps, 'model_paths': models,
              'limitations': ['Saved-file inventory only; no connectivity or DRC proof.',
                             'Pad coordinates are local to the footprint; no back-side/world transform performed.',
                             'Existing filled polygons are read without refilling.']}
    assert hashlib.sha256(path.read_bytes()).hexdigest() == result['sha256']
    emit(result, args.out)


def read_netlist(path):
    root = ET.parse(path).getroot()
    if root.tag != 'export':
        raise ValueError('Expected KiCad XML netlist; export with --format kicadxml')
    components = {}
    for c in root.findall('./components/comp'):
        ref = c.attrib['ref']
        if ref in components:
            raise ValueError('Duplicate component reference: ' + ref)
        fields = {}
        for field in c.findall('./fields/field'):
            name = field.attrib.get('name', '')
            if name in fields:
                raise ValueError('Duplicate component field: '+ref+' '+name)
            fields[name] = field.text or ''
        components[ref] = {'value': c.findtext('value', ''), 'footprint': c.findtext('footprint', ''),
                           'datasheet': c.findtext('datasheet', ''), 'fields': fields,
                           'properties': {prop.attrib.get('name',''): prop.attrib.get('value','')
                                          for prop in c.findall('property')}}
    endpoints = {}
    for net in root.findall('./nets/net'):
        for node in net.findall('node'):
            key = node.attrib['ref'] + '.' + node.attrib['pin']
            item = {'net': net.attrib.get('name', ''), 'pinfunction': node.attrib.get('pinfunction', ''),
                    'pintype': node.attrib.get('pintype', '')}
            if key in endpoints:
                raise ValueError('Duplicate endpoint; inspect stacked/multi-unit pins explicitly: ' + key)
            endpoints[key] = item
    return {'components': components, 'endpoints': endpoints,
            'net_count': len(root.findall('./nets/net'))}


def netdiff(args):
    a, b = read_netlist(args.before), read_netlist(args.after)
    ac, bc = a['components'], b['components']
    ae, be = a['endpoints'], b['endpoints']
    changes = {'components_added': sorted(bc.keys()-ac.keys()),
               'components_removed': sorted(ac.keys()-bc.keys()),
               'components_changed': {k: {'before': ac[k], 'after': bc[k]} for k in ac.keys() & bc.keys() if ac[k] != bc[k]},
               'endpoints_added': sorted(be.keys()-ae.keys()), 'endpoints_removed': sorted(ae.keys()-be.keys()),
               'endpoints_changed': {k: {'before': ae[k], 'after': be[k]} for k in ae.keys() & be.keys() if ae[k] != be[k]}}
    result = {'time': now(), 'before_counts': {k: len(a[k]) for k in ('components', 'endpoints')},
              'after_counts': {k: len(b[k]) for k in ('components', 'endpoints')},
              'unchanged': not any(changes.values()), **changes,
              'note': 'Exact named-net comparison; net codes ignored. Generated unconnected-net names/renumbering can create benign differences requiring review.'}
    emit(result, args.out)
    return 0 if result['unchanged'] else 2


def hotkeys(args):
    paths = [Path(args.file).resolve()] if args.file else [p for r in config_roots()
                if r.is_dir() for p in sorted(r.rglob('*.hotkeys'))]
    terms = [t.casefold() for t in (args.query or [])]
    rows = []
    for p in paths:
        for no, line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(), 1):
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            fields = line.split('\t')
            action = fields[0]
            if terms and not any(t in line.casefold() for t in terms):
                continue
            rows.append({'file': str(p), 'line': no, 'action': action,
                         'primary': fields[1] if len(fields)>1 else None,
                         'alternate': fields[2] if len(fields)>2 else None,
                         'raw': line})
    emit({'time': now(), 'searched_files': [str(p) for p in paths], 'matches': rows,
          'note': 'Only configured file entries, not guaranteed runtime defaults. Empty means unassigned/unspecified in this file. Resolve active version and editor context; this does not change shortcuts.'}, args.out)


def summarize_check(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    result = {'kicad_version': data.get('kicad_version'),
              'ignored_checks': data.get('ignored_checks', []),
              'included_severities': data.get('included_severities', [])}
    groups = {key: data[key] for key in ('violations', 'unconnected_items', 'schematic_parity')
              if key in data}
    if 'sheets' in data and 'violations' not in groups:
        sheets = data['sheets']
        if not isinstance(sheets, list) or any(not isinstance(s,dict) or 'violations' not in s for s in sheets):
            raise ValueError('Unrecognized ERC sheets schema: '+str(path))
        groups['violations'] = [v for sheet in sheets for v in sheet['violations']]
        result['sheet_count'] = len(sheets)
    if not groups:
        raise ValueError('Unrecognized check-report schema; cannot interpret as zero violations: '+str(path))
    for key,items in groups.items():
        if not isinstance(items,list):
            raise ValueError('Expected a list of '+key+' in '+str(path))
        result[key] = {'count': len(items), 'types': dict(Counter(x.get('type', 'unknown') for x in items)),
                       'severities': dict(Counter(x.get('severity', 'unspecified') for x in items))}
    return result


def checks(args):
    project = Path(args.project).resolve()
    before = capture(project)
    cli, version = get_cli(args.cli)
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    boards = list(project.glob('*.kicad_pcb'))
    schs = list(project.glob('*.kicad_sch'))
    board = Path(args.board).resolve() if args.board else boards[0] if len(boards)==1 else None
    sch = Path(args.schematic).resolve() if args.schematic else schs[0] if len(schs)==1 else None
    if board is None and sch is None:
        raise ValueError('No unique source selected; pass --board and/or --schematic')
    logs = []
    summary = {'time': now(), 'cli': str(cli), 'version': version, 'source_snapshot': before,
               'zone_refill': False, 'logs': logs}
    try:
        if sch:
            logs.append(require_success(run([cli, 'sch', 'export', 'netlist', '--format', 'kicadxml',
                         '--output', out/'schematic.net', sch])))
            net = read_netlist(out/'schematic.net')
            summary['netlist'] = {k: len(net[k]) for k in ('components', 'endpoints')}
            logs.append(require_success(run([cli, 'sch', 'erc', '--format', 'json', '--severity-all',
                         '--output', out/'erc.json', sch])))
            summary['erc'] = summarize_check(out/'erc.json')
        else:
            summary['schematic_status'] = 'No unique root selected; pass --schematic FILE'
        if board:
            cmd = [cli, 'pcb', 'drc', '--format', 'json', '--severity-all', '--output', out/'drc.json']
            if args.parity:
                if not sch or sch.parent != board.parent or sch.stem != board.stem:
                    raise ValueError('--parity requires the selected root schematic beside the board with the same basename')
                cmd.append('--schematic-parity')
            logs.append(require_success(run(cmd+[board], timeout=300)))
            summary['drc'] = summarize_check(out/'drc.json')
        else:
            summary['pcb_status'] = 'No unique PCB selected; pass --board FILE'
        summary['completed'] = True
    except Exception as e:
        summary['completed'] = False
        summary['error'] = str(e)
        raise
    finally:
        summary['source_delta'] = diff_sources(before, capture(project))
        summary['sources_unchanged'] = not any(summary['source_delta'].values())
        write_json(out/'CHECK_VALIDATION.json', summary)
        if not summary['sources_unchanged']:
            raise RuntimeError('Source changed during check; do not restore user edits. See CHECK_VALIDATION.json')
    emit({k: v for k, v in summary.items() if k not in ('source_snapshot', 'logs')})


def fabrication(args):
    path, data, root, copper = read_board(args.board)
    before = hashlib.sha256(data).hexdigest()
    if len(copper) < 2:
        raise ValueError('No valid copper layer stack')
    has_edge = any(n.tag and n.tag.startswith('gr_') and n.first('layer')
                   and n.first('layer').atom() == 'Edge.Cuts' for n in root.children)
    if not has_edge:
        raise ValueError('No board-level Edge.Cuts shapes; define and validate the outline before manufacturing export')
    cli, version = get_cli(args.cli)
    gerber_help = require_success(run([cli, 'pcb', 'export', 'gerbers', '--help']))['stdout']
    drill_help = require_success(run([cli, 'pcb', 'export', 'drill', '--help']))['stdout']
    if '--excellon-separate-th' not in drill_help:
        raise RuntimeError('Installed CLI lacks separate PTH/NPTH support; inspect this version manually')
    base = Path(args.output).resolve()
    base.mkdir(parents=True, exist_ok=False)
    out = base/'Gerber'
    out.mkdir()
    layers = copper + ['F.Mask', 'B.Mask', 'F.SilkS', 'B.SilkS', 'Edge.Cuts']
    if args.include_paste:
        layers += ['F.Paste', 'B.Paste']
    cmd = [cli, 'pcb', 'export', 'gerbers', '--output', out, '--layers', ','.join(layers)]
    if '--subtract-soldermask' in gerber_help:
        cmd.append('--subtract-soldermask')
    manifest = {'time': now(), 'source_pcb': str(path), 'pcb_sha256_before': before,
                'cli': str(cli), 'version': version, 'copper_layers': copper, 'layers': layers,
                'origin': 'absolute for Gerber and Excellon', 'zone_refill': False,
                'interpretation': 'Exports existing saved copper. This is not an electrical, DFM, or stale-fill approval.',
                'logs': [], 'completed': False}
    try:
        manifest['logs'].append(require_success(run(cmd+[path])))
        manifest['logs'].append(require_success(run([cli, 'pcb', 'export', 'drill', '--output', out,
                 '--format', 'excellon', '--drill-origin', 'absolute', '--excellon-units', 'mm',
                 '--excellon-zeros-format', 'decimal', '--excellon-separate-th', path])))
        files = sorted(p for p in out.iterdir() if p.is_file())
        gerbers = []
        drills = []
        omitted = []
        for p in files:
            text = p.read_text(encoding='utf-8', errors='replace')
            if p.suffix.lower() == '.gbrjob':
                json.loads(text)
            elif p.suffix.lower() == '.drl':
                if not text.startswith('M48') or not text.rstrip().endswith('M30') or 'METRIC' not in text:
                    raise ValueError('Invalid Excellon header/terminator: '+p.name)
                if re.search(r'^T\d+C', text, re.M):
                    drills.append(p)
                else:
                    omitted.append(p.name)
            else:
                if '%MOMM*%' not in text or not text.rstrip().endswith('M02*'):
                    raise ValueError('Invalid Gerber unit/terminator: '+p.name)
                gerbers.append(p)
        if len(gerbers) != len(layers):
            raise ValueError('Gerber layer count mismatch; inspect output')
        all_text = '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in gerbers)
        functions = re.findall(r'%TF.FileFunction,([^%]+)\*%', all_text)
        copper_functions = [f for f in functions if f.startswith('Copper,')]
        # X2 tags are expected with default export. Do not use filename count alone.
        if len(copper_functions) != len(copper):
            raise ValueError('Copper X2 layer count does not match source')
        actual_numbers = sorted(int(re.search(r',L(\d+),', f).group(1)) for f in copper_functions)
        if actual_numbers != list(range(1, len(copper)+1)):
            raise ValueError('Gerber copper layer order is incomplete')
        manifest['omitted_empty_drill_files'] = omitted
        manifest['gerber_file_functions'] = functions
        packed = [p for p in files if p.name not in omitted]
        archive = base/(path.stem+'_fabrication.zip')
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for p in packed:
                z.write(p, arcname=p.name)
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise ValueError('ZIP CRC check failed')
        manifest.update(completed=True, zip=str(archive), zip_sha256=sha(archive),
                        files=[{'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in packed])
    except Exception as e:
        manifest['error'] = str(e)
        raise
    finally:
        manifest['pcb_sha256_after'] = sha(path)
        manifest['pcb_unchanged'] = manifest['pcb_sha256_after'] == before
        write_json(base/'EXPORT_VALIDATION.json', manifest)
        if not manifest['pcb_unchanged']:
            raise RuntimeError('PCB changed during export; do not deliver ZIP or restore user edits')
    emit({'zip': manifest['zip'], 'copper_layers': copper, 'files': len(manifest['files']),
          'pcb_unchanged': True, 'validation': str(base/'EXPORT_VALIDATION.json')})


def new_project(args):
    dest = Path(args.directory).resolve()
    name = args.name or dest.name
    if not name or name in ('.', '..') or any(c in name for c in '/\\\x00:*?"<>|'):
        raise ValueError('Project name must be a safe filename')
    if args.thickness <= 0:
        raise ValueError('Board thickness must be positive')
    cli, version = get_cli(args.cli)
    match = re.search(r'(\d+)\.', version)
    if not match or int(match.group(1)) < 8:
        raise RuntimeError('This minimal KiCad 8-format starter requires KiCad >= 8; use a version-matched template for older KiCad')
    dest.mkdir(parents=True, exist_ok=False)
    ident = str(uuid.uuid4())
    schematic = ('(kicad_sch (version 20231120) (generator "eeschema")\n'
                 f' (uuid {quote(ident)}) (paper "A4") (lib_symbols)\n'
                 ' (sheet_instances (path "/" (page "1")))\n)\n')
    layer_rows = ['(0 "F.Cu" signal)'] + [f'({i} "In{i}.Cu" signal)' for i in range(1,args.layers-1)]
    layer_rows += ['(31 "B.Cu" signal)', '(34 "B.Paste" user)', '(35 "F.Paste" user)',
                   '(36 "B.SilkS" user "b.silkscreen")', '(37 "F.SilkS" user "f.silkscreen")',
                   '(38 "B.Mask" user)', '(39 "F.Mask" user)', '(44 "Edge.Cuts" user)',
                   '(46 "B.CrtYd" user)', '(47 "F.CrtYd" user)', '(48 "B.Fab" user)', '(49 "F.Fab" user)']
    board = ('(kicad_pcb (version 20240108) (generator "pcbnew")\n'
             f' (general (thickness {args.thickness})) (paper "A4")\n'
             ' (layers '+' '.join(layer_rows)+')\n (setup (pad_to_mask_clearance 0))\n)\n')
    sources = {name+'.kicad_sch': schematic, name+'.kicad_pcb': board,
               name+'.kicad_pro': json.dumps({'meta': {'filename': name+'.kicad_pro', 'version': 1}}, indent=2)+'\n'}
    for filename, text in sources.items():
        with (dest/filename).open('x', encoding='utf-8', newline='\n') as f:
            f.write(text)
    # Validate via the installed native CLI, without upgrading or saving sources.
    class Options:
        pass
    opts = Options()
    opts.project = dest
    opts.board = dest/(name+'.kicad_pcb')
    opts.schematic = dest/(name+'.kicad_sch')
    opts.cli = str(cli)
    opts.output = dest/'reports'/'creation_check'
    opts.parity = False
    checks(opts)
    emit({'project': str(dest/(name+'.kicad_pro')), 'format': 'KiCad 8 minimal starter',
          'validated_with': version, 'layers': args.layers, 'thickness_mm': args.thickness,
          'note': 'Empty project only. No outline, components, detailed stackup, manufacturer rules or working circuit is implied.'})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('probe', help='Discover local CLI/config/hotkeys without changing settings')
    s.add_argument('--cli'); s.add_argument('--out'); s.set_defaults(func=probe)
    s = sub.add_parser('snapshot', help='Hash current KiCad sources, not a backup')
    s.add_argument('project'); s.add_argument('--out', required=True); s.set_defaults(func=snapshot)
    s = sub.add_parser('compare', help='Compare snapshot to current sources; exit 2 means differences')
    s.add_argument('manifest'); s.add_argument('--project'); s.add_argument('--out'); s.set_defaults(func=compare)
    s = sub.add_parser('inspect-board', help='Read saved board layer/object/model inventory')
    s.add_argument('board'); s.add_argument('--detail', action='store_true'); s.add_argument('--out'); s.set_defaults(func=inspect_board)
    s = sub.add_parser('netdiff', help='Compare XML netlists by component and ref.pin, ignoring numeric net codes')
    s.add_argument('before'); s.add_argument('after'); s.add_argument('--out'); s.set_defaults(func=netdiff)
    s = sub.add_parser('hotkeys', help='Search installed user.hotkeys by action ID or assigned key')
    s.add_argument('query', nargs='*'); s.add_argument('--file'); s.add_argument('--out'); s.set_defaults(func=hotkeys)
    s = sub.add_parser('check', help='Export netlist/ERC/DRC to new folder; no source saves/refill')
    s.add_argument('project'); s.add_argument('--board'); s.add_argument('--schematic');
    s.add_argument('--cli'); s.add_argument('--output', required=True); s.add_argument('--parity', action='store_true'); s.set_defaults(func=checks)
    s = sub.add_parser('export-fab', help='Export current saved copper/drills into a fresh folder and ZIP')
    s.add_argument('board'); s.add_argument('--cli'); s.add_argument('--output', required=True)
    s.add_argument('--include-paste', action='store_true'); s.set_defaults(func=fabrication)
    s = sub.add_parser('new-project', help='Create new minimal project and validate with installed KiCad >= 8')
    s.add_argument('directory'); s.add_argument('--name'); s.add_argument('--cli')
    s.add_argument('--layers', type=int, choices=(2,4,6,8), default=2)
    s.add_argument('--thickness', type=float, default=1.6); s.set_defaults(func=new_project)
    args = p.parse_args()
    return args.func(args) or 0


if __name__ == '__main__':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        sys.exit(main())
    except (ValueError, RuntimeError, FileNotFoundError, FileExistsError, NotADirectoryError,
            subprocess.TimeoutExpired, ET.ParseError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)
