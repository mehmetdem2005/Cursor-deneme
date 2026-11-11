import ast
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "addon/mobile_speed.py"


class StabilitySourceTests(unittest.TestCase):
    def setUp(self):
        self.source = MODULE.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_gpu_subdiv_disabled_and_memory_clamped(self):
        self.assertIn("'use_gpu_subdivision', False", self.source)
        self.assertIn("'gl_texture_limit', 'CLAMP_512'", self.source)

    def test_no_saved_space_rna_references(self):
        capture = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == "_capture")
        text = ast.get_source_segment(self.source, capture)
        self.assertNotIn("(\n                space,", text)
        self.assertIn("space.as_pointer()", text)

    def test_auto_viewport_changes_disabled(self):
        callback = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == "_install_menu_when_ready")
        text = ast.get_source_segment(self.source, callback)
        self.assertNotIn("_apply_profile('BALANCED'", text)

    def test_load_events_and_diagnostics_present(self):
        self.assertIn("@persistent\ndef _mobile_load_pre", self.source)
        self.assertIn("@persistent\ndef _mobile_load_post", self.source)
        self.assertIn("mobile-file-debug.log", self.source)
        self.assertIn("def _memory_heartbeat", self.source)


if __name__ == '__main__':
    unittest.main()
