import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "addon/mobile_speed.py"


class RigLiteTests(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()
        self.tree = ast.parse(self.text)

    def test_safe_texture_not_eevee(self):
        self.assertIn("('type', 'SOLID'), ('color_type', 'TEXTURE')", self.text)
        self.assertIn("wm.mobile_safe_texture", self.text)
        self.assertNotIn("('type', 'MATERIAL')", self.text)

    def test_rig_preserves_bones_and_weights(self):
        self.assertIn("bpy.context.mode not in {'POSE', 'PAINT_WEIGHT'}", self.text)
        self.assertIn("wm.mobile_rig_lite", self.text)
        self.assertIn("if key in _rig_saved_viewports:", self.text)
        self.assertNotIn("show_overlays', False", self.text)
        self.assertNotIn("show_bones', False", self.text)
        self.assertNotIn(".modifiers.remove(", self.text)
        self.assertNotIn(".vertex_groups.remove(", self.text)

    def test_mode_poll_and_save_handlers(self):
        self.assertIn("return 0.40", self.text)
        self.assertIn("bpy.app.handlers.save_pre", self.text)
        self.assertIn("bpy.app.handlers.save_post", self.text)
        self.assertIn("_rig_stop()", self.text)
        self.assertIn("bpy.utils.unregister_class(WM_OT_mobile_rig_lite)", self.text)


if __name__ == '__main__':
    unittest.main()
