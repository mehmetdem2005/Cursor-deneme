import ast
import unittest
from pathlib import Path

SRC=Path("addon/ultra_survival.py").read_text()
TREE=ast.parse(SRC)
def section(name):
    fn=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name==name)
    return ast.get_source_segment(SRC,fn)

class UltraSurvivalTests(unittest.TestCase):
    def test_minimal_runtime(self):
        self.assertIn("register(mode_tick, first_interval=1.3)",SRC)
        self.assertIn("return 1.1",section("mode_tick"))
        self.assertNotIn("depsgraph_update_post.append",SRC)
        self.assertNotIn("bpy.ops.wm.save_mainfile",SRC)
    def test_gpu_and_simplify(self):
        s=section("gpu")
        for token in ("('viewport_aa', 'OFF')","('gl_texture_limit', 'CLAMP_128')",
                      "('use_gpu_subdivision', False)","('use_simplify', True)",
                      "('simplify_subdivision', 0)","('type', 'SOLID')",
                      "('light', 'FLAT')"):
            self.assertIn(token,s)
        self.assertNotIn("'show_overlays', False",s)
    def test_safe_bones_and_paint_restore(self):
        s=section("mode_tick")
        self.assertIn("if mode == 'EDIT_ARMATURE' and arm and AUTO_BOUNDS",s)
        self.assertIn("'display_type', 'BOUNDS'",s)
        self.assertIn("restore_mesh()",s)
        self.assertNotIn(".vertices",s)
        self.assertNotIn("edit_bones",s)
    def test_recovery(self):
        self.assertIn("'auto_save_time', 3",section("autosave"))
        self.assertIn('wm.recover_auto_save',SRC)
        self.assertIn("restore()",SRC)
    def test_runtime_packaging(self):
        repack=Path("scripts/repack.sh").read_text()
        wf=Path(".github/workflows/build.yml").read_text()
        self.assertIn("addon/safe_edit.py",repack)
        self.assertIn("addon/safe_edit.py",wf)
        self.assertIn("ANDROID_BLENDER_RENDERDIV=2",wf)
if __name__=="__main__":
    unittest.main()
