import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "addon" / "mobile_speed.py"


class GltfAndMaliTests(unittest.TestCase):
    def setUp(self):
        self.src = SOURCE.read_text(encoding="utf-8")
        self.module = ast.parse(self.src)
        self.names = {n.name for n in self.module.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}

    def test_glb_import_uses_gltf_operator_not_open_mainfile(self):
        self.assertIn("WM_OT_mobile_import_gltf", self.names)
        self.assertIn("bpy.ops.import_scene.gltf('INVOKE_DEFAULT')", self.src)
        self.assertNotIn("bpy.ops.wm.open_mainfile(", self.src)
        self.assertIn("TOPBAR_MT_file.prepend(_draw_mobile_glb_import)", self.src)
        self.assertIn("TOPBAR_MT_file.remove(_draw_mobile_glb_import)", self.src)

    def test_importer_registration_and_fallback(self):
        self.assertIn("addon_utils.enable('io_scene_gltf2'", self.src)
        self.assertIn("bpy.utils.register_class(WM_OT_mobile_import_gltf)", self.src)
        self.assertIn("bpy.utils.unregister_class(WM_OT_mobile_import_gltf)", self.src)

    def test_mali_safe_is_opt_in_and_reversible(self):
        self.assertIn("('MALI_SAFE', 'Mali Safe'", self.src)
        self.assertIn("('Mali Safe (graphics glitches)', 'MALI_SAFE')", self.src)
        self.assertIn("_set_value(space.shading, 'light', 'FLAT')", self.src)
        self.assertIn("'show_floor', 'show_ortho_grid',", self.src)
        self.assertIn("'show_axis_x', 'show_axis_y')", self.src)
        self.assertIn("for space in _spaces_for_active_windows():", self.src)
        timer = next(n for n in self.module.body if isinstance(n, ast.FunctionDef) and n.name == "_install_menu_when_ready")
        segment = ast.get_source_segment(self.src, timer)
        self.assertNotIn("_apply_profile('MALI_SAFE'", segment)


if __name__ == "__main__":
    unittest.main()
