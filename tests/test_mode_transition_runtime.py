"""Exercise the shipped Safe Edit GPU guard with a fake bpy object.

This cannot prove Android Vulkan stability, but it verifies that switching
Object -> Mesh Edit / Armature Edit / Pose / Weight Paint never triggers
Python viewport writes, including after a profile was previously applied.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE = Path("addon/safe_edit.py").read_text()
TREE = ast.parse(SOURCE)


class Tracked:
    def __init__(self, **values):
        object.__setattr__(self, 'writes', [])
        for name, value in values.items():
            object.__setattr__(self, name, value)

    def __setattr__(self, name, value):
        self.writes.append((name, value))
        object.__setattr__(self, name, value)


class ModeTransitionGuardTests(unittest.TestCase):
    def setUp(self):
        self.system = Tracked(viewport_aa='FXAA', anisotropic_filter='FILTER_2',
                              gl_texture_limit='CLAMP_512', use_gpu_subdivision=True)
        self.shading = Tracked(type='SOLID', light='STUDIO', color_type='MATERIAL',
                               show_shadows=True, show_cavity=True,
                               show_specular_highlight=True)
        self.overlay = Tracked(show_floor=True, show_ortho_grid=True,
                               show_axis_x=True, show_axis_y=True,
                               show_relationship_lines=True, show_motion_paths=True)
        self.space = SimpleNamespace(as_pointer=lambda: 100,
                                      shading=self.shading, overlay=self.overlay)
        self.context = SimpleNamespace(
            mode='OBJECT',
            preferences=SimpleNamespace(system=self.system))
        self.bpy = SimpleNamespace(context=self.context,
                                    app=SimpleNamespace(background=False))
        funcs = [node for node in TREE.body
                 if isinstance(node, ast.FunctionDef)
                 and node.name in ('apply_low_gpu', 'set_value')]
        self.module = {
            'bpy': self.bpy, 'ENABLED': True,
            'PREVIOUS_SYSTEM': {}, 'PREVIOUS_VIEW': {},
            'viewports': lambda: [self.space],
        }
        exec(compile(ast.Module(body=funcs, type_ignores=[]),
                     'safe_edit_mode_guard.py', 'exec'), self.module)

    def writes(self):
        return sum(len(x.writes) for x in (self.system, self.shading, self.overlay))

    def test_edit_pose_weight_have_zero_mutations_from_fresh_start(self):
        for mode in ('EDIT_MESH', 'EDIT_ARMATURE', 'POSE', 'PAINT_WEIGHT'):
            self.context.mode = mode
            self.assertFalse(self.module['apply_low_gpu']())
            self.assertEqual(self.writes(), 0, mode)

    def test_mode_entry_after_object_profile_never_changes_viewport(self):
        self.assertTrue(self.module['apply_low_gpu']())
        self.assertEqual(self.shading.light, 'FLAT')
        self.assertEqual(self.system.viewport_aa, 'OFF')
        before = self.writes()
        for mode in ('EDIT_MESH', 'EDIT_ARMATURE', 'PAINT_WEIGHT', 'POSE'):
            self.context.mode = mode
            self.assertFalse(self.module['apply_low_gpu']())
            self.assertEqual(self.writes(), before, mode)

    def test_safe_apply_is_idempotent(self):
        self.assertTrue(self.module['apply_low_gpu']())
        before = self.writes()
        self.assertTrue(self.module['apply_low_gpu']())
        self.assertEqual(self.writes(), before)


if __name__ == '__main__':
    unittest.main()
