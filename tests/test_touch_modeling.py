"""Static safety checks for opt-in Android touch diagnosis (not a device test)."""
import ast
import pathlib
import unittest

SRC = pathlib.Path("addon/touch_modeling.py").read_text()
TREE = ast.parse(SRC)


def function(name):
    return next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == name)


class TouchDiagnosticsTests(unittest.TestCase):
    def test_diagnostic_is_opt_in_and_no_polling(self):
        self.assertIn("_TRACE_ACTIVE = False", SRC)
        self.assertIn("modal_handler_add(self)", SRC)
        self.assertIn('return {"PASS_THROUGH"}', SRC)
        self.assertNotIn("depsgraph_update_post", SRC)
        self.assertNotIn("bpy.ops.object.mode_set", SRC)
        self.assertNotIn("bpy.ops.wm.save_mainfile", SRC)
        self.assertIn("deque(maxlen=400)", SRC)

    def test_native_transform_used_instead_of_manual_geometry_edits(self):
        self.assertIn('bpy.ops.transform.resize("EXEC_DEFAULT"', SRC)
        self.assertIn('bpy.ops.transform.resize("INVOKE_DEFAULT")', SRC)
        self.assertIn("with context.temp_override(", SRC)
        self.assertNotIn("v.co =", SRC)
        self.assertNotIn("vertex_groups", SRC)
        self.assertNotIn("modifiers", SRC)

    def test_selection_and_mode_guard(self):
        self.assertIn('context.mode == "EDIT_MESH"', SRC)
        self.assertIn("if not _selected(context):", SRC)
        self.assertIn("_viewport_region(context)", SRC)
        self.assertIn("mesh_delta", SRC)

    def test_installed_in_signed_apk_path(self):
        self.assertIn("addon/touch_modeling.py", pathlib.Path("scripts/repack.sh").read_text())
        self.assertIn("EXTRA_ENTRY", pathlib.Path("scripts/patch_runtime.py").read_text())
        self.assertIn("addon/touch_modeling.py", pathlib.Path(".github/workflows/build.yml").read_text())

    def test_diagnostics_release_requires_manual_publish(self):
        wf = pathlib.Path(".github/workflows/build.yml").read_text()
        self.assertIn("inputs.publish_release == true", wf)
        self.assertIn("Touch Diagnostic Experiment", wf)


if __name__ == "__main__":
    unittest.main()
