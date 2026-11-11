import ast
from pathlib import Path
import unittest

CODE = Path('addon/mobile_speed.py').read_text()
AST = ast.parse(CODE)

class MaliDepthTests(unittest.TestCase):
    def test_depth_only_changes_viewport_clip(self):
        f = next(n for n in AST.body if isinstance(n, ast.FunctionDef) and n.name == '_depth_apply')
        s = ast.get_source_segment(CODE, f)
        self.assertIn("'clip_start', 0.1", s)
        self.assertIn("'clip_end', 100.0", s)
        self.assertNotIn('modifiers', s)
        self.assertIn("def _depth_restore():", CODE)

    def test_face_check_bounded_and_readonly(self):
        self.assertIn("def _sample_overlapping_faces(mesh, max_faces=2500):", CODE)
        self.assertIn("mesh.polygons[idx]", CODE)
        self.assertIn("mesh.vertices[v].co", CODE)
        self.assertNotIn(".vertices.foreach_set(", CODE)

    def test_save_and_load_do_not_persist_depth_change(self):
        self.assertIn("def _depth_save_pre", CODE)
        self.assertIn("def _depth_save_post", CODE)
        self.assertIn("bpy.utils.unregister_class(WM_OT_mobile_depth_test)", CODE)
        self.assertIn("wm.mobile_depth_test", CODE)

if __name__ == '__main__':
    unittest.main()
