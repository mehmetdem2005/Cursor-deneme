"""Mode-safe, reversible depth range checks for the shipped Blender add-on.

Unit tests mock bpy; they do not claim an Android Mali Vulkan device test.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE = Path('addon/safe_edit.py').read_text()
TREE = ast.parse(SOURCE)


class Watch:
    def __init__(self, start=0.01, end=1000.0, ptr=1):
        self.writes = []
        self.clip_start = start
        self.clip_end = end
        self.ptr = ptr

    def as_pointer(self):
        return self.ptr

    def __setattr__(self, key, value):
        if key in ('clip_start', 'clip_end') and hasattr(self, 'writes'):
            self.writes.append((key, value))
        super().__setattr__(key, value)


class TestDepthGuard(unittest.TestCase):
    def setUp(self):
        self.spaces = [Watch(ptr=1), Watch(start=0.001, end=5000, ptr=2)]
        fns = ('set_value', 'apply_depth_profile', 'restore_depth_profile')
        nodes = [n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in fns]
        self.scope = {
            'DEPTH_PROFILE': 'SAFE',
            'DEPTH_RANGES': {'SAFE': (0.05, 50.0), 'STRONG': (0.1, 20.0)},
            'PREVIOUS_CLIP': {},
            'all_viewports': lambda: self.spaces,
        }
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<depth>', 'exec'),
             self.scope)
        self.ctx = SimpleNamespace(mode='OBJECT')

    def run_profile(self):
        return self.scope['apply_depth_profile'](self.ctx)

    def test_safe_default_is_one_shot(self):
        self.assertEqual(self.run_profile(), 2)
        for s in self.spaces:
            self.assertEqual((s.clip_start, s.clip_end), (0.05, 50.0))
        self.assertEqual(self.scope['PREVIOUS_CLIP'],
                         {1: (0.01, 1000.0), 2: (0.001, 5000.0)})
        before = [len(s.writes) for s in self.spaces]
        self.run_profile()
        self.assertEqual([len(s.writes) for s in self.spaces], before)

    def test_strong_then_restore_original(self):
        self.run_profile()
        self.scope['DEPTH_PROFILE'] = 'STRONG'
        self.run_profile()
        for s in self.spaces:
            self.assertEqual((s.clip_start, s.clip_end), (0.1, 20.0))
        self.assertEqual(self.scope['restore_depth_profile'](self.ctx), 2)
        self.assertEqual((self.spaces[0].clip_start, self.spaces[0].clip_end),
                         (0.01, 1000.0))
        self.assertEqual((self.spaces[1].clip_start, self.spaces[1].clip_end),
                         (0.001, 5000.0))
        self.assertEqual(self.scope['PREVIOUS_CLIP'], {})

    def test_never_write_in_pose_weight_edit_sculpt(self):
        for mode in ('EDIT_MESH', 'EDIT_ARMATURE', 'POSE', 'PAINT_WEIGHT',
                     'PAINT_TEXTURE', 'SCULPT'):
            ctx = SimpleNamespace(mode=mode)
            self.assertEqual(self.scope['apply_depth_profile'](ctx), 0)
            self.assertEqual(self.scope['restore_depth_profile'](ctx), 0)
        self.assertEqual(sum(len(s.writes) for s in self.spaces), 0)

    def test_off_does_not_apply(self):
        self.scope['DEPTH_PROFILE'] = 'OFF'
        self.assertEqual(self.run_profile(), 0)
        self.assertEqual(sum(len(s.writes) for s in self.spaces), 0)

    def test_no_data_or_native_gpu_changes(self):
        depth = next(ast.get_source_segment(SOURCE, n) for n in TREE.body
                     if isinstance(n, ast.FunctionDef)
                     and n.name == 'apply_depth_profile')
        self.assertIn("context.mode != 'OBJECT'", depth)
        for forbidden in ('bpy.ops.', '.modifiers', '.vertex_groups',
                          '.edit_bones', 'renderdiv', 'texture_limit',
                          '.vertices', 'depsgraph_update_post'):
            self.assertNotIn(forbidden, depth)
        self.assertIn('apply_depth_profile(bpy.context)', SOURCE)
        self.assertIn("DEPTH_PROFILE = 'SAFE'", SOURCE)

    def test_existing_optimizations_unchanged(self):
        for required in ("('viewport_aa', 'OFF')",
                         "('gl_texture_limit', 'CLAMP_128')",
                         "('use_gpu_subdivision', False)",
                         "('auto_save_time', 3)"):
            self.assertIn(required, SOURCE)


if __name__ == '__main__':
    unittest.main()
