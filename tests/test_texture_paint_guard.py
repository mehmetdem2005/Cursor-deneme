"""Real behavior checks on shipped paint preflight with mocked Blender RNA.

These tests validate Python behavior, not the native Android GPU driver.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

SRC = Path('addon/safe_edit.py').read_text()
TREE = ast.parse(SRC)


class Tracked:
    def __init__(self, **props):
        object.__setattr__(self, 'writes', [])
        for k, v in props.items():
            object.__setattr__(self, k, v)

    def __setattr__(self, name, value):
        self.writes.append((name, value))
        object.__setattr__(self, name, value)


class PaintPreflightTests(unittest.TestCase):
    def setUp(self):
        self.sh = [Tracked(type='MATERIAL', light='STUDIO',
                           color_type='MATERIAL', show_shadows=True,
                           show_cavity=True, show_specular_highlight=True)
                   for _ in range(2)]
        self.ov = [Tracked(show_floor=True, show_ortho_grid=True,
                           show_axis_x=True, show_axis_y=True,
                           show_relationship_lines=True, show_motion_paths=True)
                   for _ in range(2)]
        self.spaces = [SimpleNamespace(
            as_pointer=lambda n=n: n+123, shading=self.sh[n], overlay=self.ov[n])
                       for n in range(2)]
        screens = [SimpleNamespace(areas=[
            SimpleNamespace(type='VIEW_3D',
                            spaces=SimpleNamespace(active=sp))])
                   for sp in self.spaces]
        self.bpy = SimpleNamespace(data=SimpleNamespace(screens=screens))
        selected = ('set_value', 'all_viewports', 'paint_capture',
                    'apply_paint_profile')
        code = [n for n in TREE.body if isinstance(n, ast.FunctionDef)
                and n.name in selected]
        self.scope = {'bpy': self.bpy, 'ENABLED': True, 'PREVIOUS_VIEW': {},
                      'apply_low_gpu': lambda: None}
        exec(compile(ast.Module(body=code, type_ignores=[]),
                     'paint_preflight.py', 'exec'), self.scope)

    def changes(self):
        return sum(len(x.writes) for x in self.sh+self.ov)

    def test_all_screens_safe_solid_without_eevee(self):
        self.assertEqual(self.scope['apply_paint_profile'](
            SimpleNamespace(mode='OBJECT')), 2)
        self.assertTrue(all(x.type == 'SOLID' and x.light == 'FLAT'
                            for x in self.sh))
        self.assertTrue(all(x.color_type == 'MATERIAL' for x in self.sh))
        self.assertTrue(all(not x.show_cavity for x in self.sh))
        self.assertEqual(len(self.scope['PREVIOUS_VIEW']), 2)

    def test_zero_writes_during_paint_edit_weight_and_pose(self):
        for mode in ('PAINT_TEXTURE', 'PAINT_WEIGHT', 'EDIT_MESH', 'POSE',
                     'SCULPT', 'EDIT_ARMATURE'):
            self.assertEqual(self.scope['apply_paint_profile'](
                SimpleNamespace(mode=mode)), 0)
        self.assertEqual(self.changes(), 0)

    def test_repeated_prep_is_idempotent(self):
        ctx = SimpleNamespace(mode='OBJECT')
        self.scope['apply_paint_profile'](ctx)
        before = self.changes()
        self.scope['apply_paint_profile'](ctx)
        self.assertEqual(self.changes(), before)

    def test_opt_in_texture_only_remains_solid(self):
        self.scope['apply_paint_profile'](
            SimpleNamespace(mode='OBJECT'), textured=True)
        self.assertTrue(all(x.type == 'SOLID' and x.color_type == 'TEXTURE'
                            for x in self.sh))

    def test_no_data_mutation_or_mode_poll(self):
        for token in ('bpy.ops.object.mode_set', 'bpy.ops.paint',
                      '.vertex_groups', '.edit_bones', 'depsgraph_update_post',
                      'bpy.app.timers.register(mode_tick'):
            self.assertNotIn(token, SRC)
        self.assertIn("context.mode == 'OBJECT'", SRC)
        self.assertIn('paint_diagnostic', SRC)
        self.assertIn("wm.prepare_texture_paint", SRC)
        self.assertIn("wm.safe_texture_preview", SRC)
        self.assertIn('for screen in bpy.data.screens:', SRC)

    def test_diagnostic_never_logs_file_names(self):
        segment = next(ast.get_source_segment(SRC, n) for n in TREE.body
                       if isinstance(n, ast.FunctionDef)
                       and n.name == 'paint_diagnostic')
        self.assertNotIn('obj.name', segment)
        self.assertNotIn('filepath', segment)
        self.assertNotIn('bpy.ops.', segment)


if __name__ == '__main__':
    unittest.main()
