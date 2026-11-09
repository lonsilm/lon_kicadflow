#!/usr/bin/env python3
"""Capture saved PCB geometry/connectivity using matching KiCad pcbnew Python.

No saves, fills or design mutations. Run with KiCad's matching Python runtime.
Tested on KiCad 10; inspect diagnostics for version-dependent methods.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

from kicad_ops import sha, write_json


def xy(v):
    return [v.x/1e6, v.y/1e6]


def polygon(ps):
    def ring(chain):
        pts = [xy(chain.CPoint(i)) for i in range(chain.PointCount())]
        if pts and pts[-1] != pts[0]:
            pts.append(pts[0])
        return pts
    return {'type': 'MultiPolygon', 'coordinates': [
        [ring(ps.COutline(i))] + [ring(ps.CHole(i,j)) for j in range(ps.HoleCount(i))]
        for i in range(ps.OutlineCount())]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('board')
    parser.add_argument('--output', required=True)
    parser.add_argument('--connectivity', action='store_true', help='Also inspect native pad connectivity, not signal integrity')
    args = parser.parse_args()
    try:
        import pcbnew as p
    except ImportError as e:
        raise RuntimeError('Use Python with the matching KiCad pcbnew binding; this script does not install it') from e
    source = Path(args.board).resolve()
    before = sha(source)
    start = datetime.now(timezone.utc).astimezone().isoformat()
    b = p.LoadBoard(str(source))
    try:
        layers = list(b.GetEnabledLayers().CuStack())
    except AttributeError:
        layers = [i for i in range(p.PCB_LAYER_ID_COUNT) if b.IsLayerEnabled(i) and p.IsCopperLayer(i)]
    layer_names = {i: b.GetLayerName(i) for i in layers}
    result = {'source': str(source), 'sha256_before': before, 'read_start': start,
              'tool': 'pcbnew '+p.Version(), 'units': 'mm', 'source_state': 'saved PCB; no refill/save',
              'copper_layers': [layer_names[i] for i in layers],
              'footprints': [], 'objects': [], 'ground_regions': [], 'warnings': []}
    netpads = {}
    for f in b.GetFootprints():
        ref = f.GetReference()
        result['footprints'].append({'reference': ref, 'value': f.GetValue(),
            'footprint': f.GetFPIDAsString(), 'position_mm': xy(f.GetPosition()),
            'angle_deg': f.GetOrientationDegrees(), 'layer': b.GetLayerName(f.GetLayer())})
        for pad in f.Pads():
            ls = [i for i in layers if pad.IsOnLayer(i)]
            result['objects'].append({'id': pad.m_Uuid.AsString(), 'kind': 'pad',
                'reference': ref, 'pin': pad.GetNumber(), 'net': pad.GetNetname(),
                'position_mm': xy(pad.GetPosition()), 'layers': [layer_names[i] for i in ls],
                'drill_mm': xy(pad.GetDrillSize()),
                'polygons_by_layer': {layer_names[i]: polygon(pad.GetEffectivePolygon(i)) for i in ls}})
            if pad.GetNetname() and not pad.GetNetname().startswith('unconnected-'):
                netpads.setdefault(pad.GetNetname(), []).append(pad)
    for t in b.GetTracks():
        common = {'id': t.m_Uuid.AsString(), 'net': t.GetNetname()}
        if isinstance(t,p.PCB_VIA):
            try:
                width = t.GetWidth(p.F_Cu)
            except TypeError:
                width = t.GetWidth()
            result['objects'].append(dict(common, kind='via', position_mm=xy(t.GetPosition()),
                diameter_mm=width/1e6, drill_mm=t.GetDrillValue()/1e6,
                layers=[layer_names[i] for i in layers if t.IsOnLayer(i)]))
        elif isinstance(t,p.PCB_ARC):
            result['objects'].append(dict(common, kind='arc', start_mm=xy(t.GetStart()),
                mid_mm=xy(t.GetMid()), end_mm=xy(t.GetEnd()), width_mm=t.GetWidth()/1e6,
                layers=[b.GetLayerName(t.GetLayer())]))
        else:
            result['objects'].append(dict(common, kind='track', start_mm=xy(t.GetStart()),
                end_mm=xy(t.GetEnd()), width_mm=t.GetWidth()/1e6,
                layers=[b.GetLayerName(t.GetLayer())]))
    for z in b.Zones():
        for ly in layers:
            if not z.IsOnLayer(ly):
                continue
            if z.GetIsRuleArea():
                result['objects'].append({'id': z.m_Uuid.AsString(), 'kind': 'rule_area',
                    'net': z.GetNetname(), 'layers': [layer_names[ly]], 'geometry': polygon(z.Outline()),
                    'note': 'Read actual rule-area flags before treating this as a universal keepout'})
            elif z.HasFilledPolysForLayer(ly):
                ps = z.GetFilledPolysList(ly)
                result['objects'].append({'id': z.m_Uuid.AsString(), 'kind': 'zone_fill',
                    'net': z.GetNetname(), 'layers': [layer_names[ly]], 'geometry': polygon(ps)})
                if z.GetNetname() == 'GND':
                    for i in range(ps.OutlineCount()):
                        result['ground_regions'].append({'zone': z.m_Uuid.AsString(),
                            'layer': layer_names[ly], 'polygon_index': i,
                            'native_island': bool(z.IsIsland(ly,i))})
            else:
                result['warnings'].append(f'No saved fill: zone {z.m_Uuid.AsString()} layer {layer_names[ly]}')
    outline = p.SHAPE_POLY_SET()
    try:
        ok = b.GetBoardPolygonOutlines(outline,False)
        result['board_outline'] = polygon(outline) if ok and outline.OutlineCount() else None
    except Exception as e:
        result['board_outline'] = None
        result['warnings'].append('Outline API: '+str(e))
    if args.connectivity:
        missing = {}
        conn = b.GetConnectivity()
        for net,pads in netpads.items():
            reached = {item.m_Uuid.AsString() for item in conn.GetConnectedItems(pads[0])}
            reached.add(pads[0].m_Uuid.AsString())
            absent = [f'{pad.GetParentFootprint().GetReference()}.{pad.GetNumber()}'
                      for pad in pads if pad.m_Uuid.AsString() not in reached]
            if absent:
                missing[net] = absent
        result['connectivity'] = {'native_graph_disconnected_pad_nets': missing,
            'nets_checked': len(netpads),
            'note': 'Native saved-copper graph only; confirm DRC and stacked-pad semantics. No high-frequency return-path proof.'}
    result['read_end'] = datetime.now(timezone.utc).astimezone().isoformat()
    result['sha256_after'] = sha(source)
    result['source_unchanged'] = before == result['sha256_after']
    result['geometry_note'] = 'Effective polygon tessellation from native API; not an impedance, 3D clearance, or exact electromagnetic solution.'
    if not result['source_unchanged']:
        raise RuntimeError('Source changed during capture; reject mixed-state report. Do not restore user edits.')
    write_json(args.output,result)
    print(json.dumps({'output': str(Path(args.output).resolve()),
        'footprints': len(result['footprints']),
        'objects': dict(Counter(x['kind'] for x in result['objects'])),
        'layers': result['copper_layers'], 'source_unchanged': True},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
