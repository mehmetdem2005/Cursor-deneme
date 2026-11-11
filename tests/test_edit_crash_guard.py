import ast
import pathlib
import unittest

SRC=pathlib.Path('addon/safe_edit.py').read_text()
TREE=ast.parse(SRC)
def fn(name):
    n=next(x for x in TREE.body if isinstance(x,ast.FunctionDef) and x.name==name)
    return ast.get_source_segment(SRC,n)

class EditCrashGuardTests(unittest.TestCase):
    def test_no_repeating_timer_or_edit_mode_writes(self):
        self.assertIn('register(initialize_once, first_interval=1.0)',SRC)
        self.assertNotIn('mode_tick',SRC)
        self.assertNotIn('depsgraph_update_post.append',SRC)
        self.assertIn("bpy.context.mode != 'OBJECT'",fn('apply_low_gpu'))
        self.assertIn("bpy.context.mode != 'OBJECT'",fn('restore_view'))

    def test_never_mutates_armatures_models_or_scene(self):
        for forbidden in ['.display_type','edit_bones','vertex_groups',
                          '.modifiers','bpy.ops.object.mode_set',
                          'use_simplify','simplify_subdivision','show_overlays']:
            self.assertNotIn(forbidden,SRC)

    def test_save_still_native_and_no_edit_autosave_operator(self):
        self.assertIn("'auto_save_time', 3",fn('configure_autosave'))
        self.assertIn("'use_auto_save_temporary_files', True",fn('configure_autosave'))
        self.assertIn("wm.recover_auto_save",SRC)
        self.assertNotIn("bpy.ops.wm.save_mainfile",SRC)

    def test_android_looper_original_call(self):
        c=pathlib.Path('native/renderdiv_shim.c').read_text()
        self.assertIn("return ALooper_pollOnce(timeoutMillis, outFd, outEvents, outData);",c)
        self.assertNotIn('last_event_ms',c)
        self.assertIn('"debug.blender.renderdiv"',c)

    def test_exact_module_is_packaged(self):
        repack=pathlib.Path('scripts/repack.sh').read_text()
        workflow=pathlib.Path('.github/workflows/build.yml').read_text()
        self.assertIn('addon/safe_edit.py',repack)
        self.assertIn('addon/safe_edit.py',workflow)
        self.assertIn('ANDROID_BLENDER_RENDERDIV=2',workflow)

if __name__=='__main__':
    unittest.main()
