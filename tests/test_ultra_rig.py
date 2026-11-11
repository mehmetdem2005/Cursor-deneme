import ast
from pathlib import Path
import unittest

PY = Path('addon/mobile_speed.py').read_text()
C = Path('native/renderdiv_shim.c').read_text()
SH = Path('scripts/install_renderdiv.sh').read_text()
WORKFLOW = Path('.github/workflows/build.yml').read_text()
MODULE = ast.parse(PY)

def function(name):
    n = next(n for n in MODULE.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(PY, n)

class UltraRigTests(unittest.TestCase):
    def test_max_supported_render_scale_and_android_lowmem_override(self):
        self.assertIn("export ANDROID_BLENDER_RENDERDIV=4", WORKFLOW)
        self.assertIn("#if MOBILE_RENDER_DIVISOR < 1 || MOBILE_RENDER_DIVISOR > 4", C)
        self.assertIn("value[0] = '4';", C)
        self.assertIn('"debug.blender.lowmem"', C)
        self.assertIn('"debug.blender.renderdiv"', C)
        self.assertIn('"4"', SH)

    def test_viewport_only_and_preserve_work_tools(self):
        s = function('_ultra_rig_apply')
        self.assertIn("'type', 'SOLID'", s)
        self.assertIn("'light', 'FLAT'", s)
        self.assertIn("_ULTRA_OV_FIELDS", s)
        for forbidden in ["show_overlays', False", "show_bones', False",
                          "show_extras', False", ".vertices", ".vertex_groups",
                          ".edit_bones", ".modifiers"]:
            self.assertNotIn(forbidden, s)
        self.assertIn("'gl_texture_limit', 'CLAMP_128'", PY)
        self.assertIn("'anisotropic_filter', 'FILTER_0'", PY)

    def test_initial_and_loaded_file_mode(self):
        self.assertIn("_ultra_rig_apply()", function('_install_menu_when_ready'))
        self.assertIn("_ultra_rig_apply()", function('_mobile_load_post'))
        self.assertIn("_ultra_rig_restore()", function('_mobile_load_pre'))

    def test_no_gpu_mode_switch_during_auto_or_manual_save(self):
        self.assertNotIn("_ultra_rig_save_pre", PY)
        self.assertNotIn("_ultra_rig_save_post", PY)
        self.assertIn("_ultra_rig_restore()", function('_mobile_load_pre'))
        self.assertIn("_ultra_rig_restore()", function('unregister'))

    def test_autosave_remains_three_minute(self):
        self.assertIn("paths.auto_save_time = 3", PY)
        self.assertIn("'wm.recover_auto_save'", PY)

if __name__ == '__main__':
    unittest.main()
