"""Meaningful stdlib tests for helper invariants; no existing user designs used."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest

import kicad_ops as ops
from sexpr_read import parse, quote


class HelperTests(unittest.TestCase):
    def test_strings_spans_and_truncated_source(self):
        value = '中文 (pad) "quote" \\path\nnext'
        source = '; header\n(root (property "Name" '+quote(value)+'))'
        n = parse(source).first('property')
        self.assertEqual(n.atom(2),value)
        self.assertEqual(parse(source[n.start:n.end]).atom(2),value)
        self.assertEqual(parse('(x "a\\q")').atom(),'a\\q')
        for broken in ('(root', '(x "bad)', '(x))', '(x) (y)'):
            with self.assertRaises(ValueError):
                parse(broken)

    def test_report_never_overwrites_or_targets_design(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ('board.kicad_pcb','project.kicad_pro','sym-lib-table'):
                p = root/name
                p.write_text('protected',encoding='utf-8')
                with self.assertRaises(ValueError):
                    ops.write_json(p,{'changed':True})
                self.assertEqual(p.read_text(), 'protected')
            report = root/'report.json'
            ops.write_json(report,{'a':1})
            with self.assertRaises(FileExistsError):
                ops.write_json(report,{'a':2})
            self.assertEqual(json.loads(report.read_text()),{'a':1})

    def test_source_changes_detected_while_generated_files_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root/'board.kicad_pcb'
            source.write_text('(kicad_pcb)',encoding='utf-8')
            first = ops.capture(root)
            (root/'reports').mkdir()
            (root/'reports'/'temporary.kicad_pcb').write_text('derived',encoding='utf-8')
            self.assertFalse(any(ops.diff_sources(first,ops.capture(root)).values()))
            source.write_text('(kicad_pcb (version 1))',encoding='utf-8')
            self.assertEqual(ops.diff_sources(first,ops.capture(root))['changed'],['board.kicad_pcb'])

    def test_net_codes_ignored_actual_pin_changes_retained(self):
        template = '<export><components><comp ref="U1"><value>MCU</value><footprint>L:P</footprint></comp></components><nets><net code="{code}" name="{net}"><node ref="U1" pin="1" pinfunction="VDD" pintype="power_in"/></net></nets></export>'
        with tempfile.TemporaryDirectory() as d:
            a,b,c = [Path(d)/name for name in ('a.net','b.net','c.net')]
            a.write_text(template.format(code=1,net='VDD'),encoding='utf-8')
            b.write_text(template.format(code=99,net='VDD'),encoding='utf-8')
            c.write_text(template.format(code=99,net='GND'),encoding='utf-8')
            self.assertEqual(ops.read_netlist(a),ops.read_netlist(b))
            self.assertNotEqual(ops.read_netlist(a)['endpoints'],ops.read_netlist(c)['endpoints'])
            b.write_text(template.format(code=99,net='VDD').replace('</comp>', '<fields><field name="MPN">ActualPart</field></fields></comp>'),encoding='utf-8')
            self.assertNotEqual(ops.read_netlist(a)['components'],ops.read_netlist(b)['components'])
            duplicate = template.format(code=1,net='VDD').replace('</net>', '<node ref="U1" pin="1"/></net>')
            b.write_text(duplicate,encoding='utf-8')
            with self.assertRaises(ValueError):
                ops.read_netlist(b)

    def test_copper_layers_order_not_serialized_numeric_ids(self):
        source = '(kicad_pcb (version 20260101) (layers (2 "B.Cu" signal) (6 "In2.Cu" signal) (0 "F.Cu" signal) (4 "In1.Cu" signal)))'
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'board.kicad_pcb'
            p.write_text(source,encoding='utf-8')
            before = ops.sha(p)
            self.assertEqual(ops.read_board(p)[3],['F.Cu','In1.Cu','In2.Cu','B.Cu'])
            self.assertEqual(ops.sha(p),before)

    def test_erc_per_sheet_schema_not_misreported_as_zero(self):
        with tempfile.TemporaryDirectory() as d:
            report = Path(d)/'erc.json'
            report.write_text(json.dumps({'sheets':[
                {'path':'/', 'violations':[]},
                {'path':'/Power/', 'violations':[{'type':'power_pin_not_driven','severity':'error'}]}
            ]}),encoding='utf-8')
            self.assertEqual(ops.summarize_check(report)['violations']['count'],1)
            self.assertEqual(ops.summarize_check(report)['sheet_count'],2)
            report.write_text('{"unexpected_new_schema":[]}',encoding='utf-8')
            with self.assertRaises(ValueError):
                ops.summarize_check(report)


if __name__ == '__main__':
    unittest.main()
