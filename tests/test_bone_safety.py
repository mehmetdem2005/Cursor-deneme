import ast
import pathlib
import unittest

SRC = pathlib.Path("addon/mobile_speed.py").read_text(encoding="utf-8")
MODULE = ast.parse(SRC)


def fragment(name):
    node = next(x for x in MODULE.body if isinstance(x, ast.FunctionDef) and x.name == name)
    return ast.get_source_segment(SRC, node)


class AndroidBoneDiagnosticTests(unittest.TestCase):
    def test_stick_bone_draw_path(self):
        self.assertIn("'display_type', 'STICK'", fragment("_bone_safe_set"))
        self.assertIn("'display_type', 'BOUNDS'", fragment("_bone_safe_set"))
        self.assertIn("def _bone_safe_armature(context):", SRC)

    def test_bones_and_weights_are_never_mutated(self):
        for token in ("edit_bones.remove(", "edit_bones.new(", "bpy.ops.armature.delete(",
                      "vertex_groups.remove(", "vertex_groups.add(", "pose.bones.clear("):
            self.assertNotIn(token, SRC)

    def test_observability_is_bounded_and_pointer_safe(self):
        s = fragment("_bone_safe_watch")
        self.assertIn("return 0.75", s)
        self.assertIn("BONE_COUNT_{}_{}", s)
        self.assertIn("len(data.edit_bones)", fragment("_bone_safe_count"))
        self.assertNotIn("bpy.app.handlers.depsgraph_update_post", SRC)

    def test_session_restores_before_saving_and_on_file_load(self):
        self.assertIn("def _bone_safe_save_pre(", SRC)
        self.assertIn("def _bone_safe_save_post(", SRC)
        self.assertIn("_bone_safe_set(is_restore=True)", SRC)
        self.assertIn("_bone_safe_stop()", fragment("_mobile_load_pre"))
        self.assertIn("bpy.utils.unregister_class(WM_OT_mobile_bone_safety)", SRC)

    def test_ui_is_explicit_not_automatic(self):
        self.assertIn("Bone Safe: Stick (lightweight)", SRC)
        self.assertIn("Bone Safe: Isolate Mesh (bounds)", SRC)
        self.assertIn("Bone Safe: OFF / Restore", SRC)
        self.assertNotIn("_bone_safe_set(is_restore=False)", fragment("_install_menu_when_ready"))


if __name__ == "__main__":
    unittest.main()
