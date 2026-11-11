import ast
from pathlib import Path
import unittest

SOURCE = Path('addon/mobile_speed.py').read_text(encoding='utf-8')
AST = ast.parse(SOURCE)


def fn(name):
    node = next(n for n in AST.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(SOURCE, node)


class CrashRecoveryAutosaveTests(unittest.TestCase):
    def test_native_interval_is_three_minutes(self):
        block = fn('_configure_three_minute_autosave')
        self.assertIn('paths.use_auto_save_temporary_files = True', block)
        self.assertIn('paths.auto_save_time = 3', block)
        self.assertIn('paths.save_version = 2', block)

    def test_applies_on_launch_and_after_blend_load(self):
        self.assertIn('_configure_three_minute_autosave()', fn('register'))
        self.assertIn('_configure_three_minute_autosave()', fn('_mobile_load_post'))

    def test_recovery_access_is_blender_operator(self):
        menu = fn('_draw_mobile_glb_import')
        self.assertIn("'wm.recover_auto_save'", menu)
        self.assertIn("self.layout.operator_context = 'INVOKE_DEFAULT'", menu)

    def test_avoids_periodic_python_file_save_during_active_rig_editing(self):
        autosave = fn('_configure_three_minute_autosave')
        self.assertNotIn('bpy.ops.wm.save_as_mainfile', autosave)
        self.assertNotIn('bpy.ops.wm.save_mainfile', autosave)
        self.assertNotIn('bpy.app.timers.register', autosave)

    def test_does_not_overwrite_original_project(self):
        autosave = fn('_configure_three_minute_autosave')
        self.assertNotIn('bpy.data.filepath =', autosave)
        self.assertNotIn('bpy.ops.wm.open_mainfile', autosave)


if __name__ == '__main__':
    unittest.main()
