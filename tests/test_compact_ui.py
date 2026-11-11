import unittest
from pathlib import Path

class MobileUsabilityRegressionTests(unittest.TestCase):
    def test_reject_quadruple_framebuffer_downscale(self):
        workflow = Path(".github/workflows/build.yml").read_text()
        self.assertIn("export ANDROID_BLENDER_RENDERDIV=2", workflow)
        self.assertNotIn("export ANDROID_BLENDER_RENDERDIV=4", workflow)

    def test_ui_density_override_is_app_local_and_supported(self):
        c = Path("native/renderdiv_shim.c").read_text()
        self.assertIn('strcmp(name, "debug.blender.uidpi") == 0', c)
        self.assertIn("value[0] = '9';", c)
        self.assertIn("value[1] = '6';", c)
        self.assertIn("return 2;", c)
        self.assertIn('strcmp(name, "debug.blender.lowmem") == 0', c)
        self.assertIn('strcmp(name, "debug.blender.renderdiv") == 0', c)
        self.assertIn('return __system_property_get(name, value);', c)

    def test_edit_mode_has_reference_model_by_default(self):
        src = Path("addon/ultra_survival.py").read_text()
        self.assertIn("AUTO_BOUNDS = False", src)
        self.assertIn("if mode == 'EDIT_ARMATURE' and arm and AUTO_BOUNDS:", src)
        self.assertIn("restore_mesh()", src)
        self.assertNotIn("show_overlays', False", src)

    def test_keep_gpu_limits_and_autosave(self):
        src = Path("addon/ultra_survival.py").read_text()
        for item in ["('viewport_aa', 'OFF')","('gl_texture_limit', 'CLAMP_128')",
                     "('simplify_subdivision', 0)","('type', 'SOLID')",
                     "'auto_save_time', 3"]:
            self.assertIn(item, src)
        repack = Path("scripts/repack.sh").read_text()
        self.assertIn("addon/ultra_survival.py", repack)

if __name__ == '__main__':
    unittest.main()
