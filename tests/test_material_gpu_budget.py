"""Offline unit tests: never run Blender or touch the GPU."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

source = Path("addon/safe_edit.py").read_text()
tree = ast.parse(source)
spec = importlib.util.spec_from_file_location("shadow_patch", "scripts/patch_mobile_shadow_pool.py")
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class Eevee:
    def __init__(self, value):
        self.shadow_pool_size = value


class Tests(unittest.TestCase):
    def setUp(self):
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                        and n.name == "cap_mobile_eevee_shadow_pool")
        self.scenes = [
            SimpleNamespace(eevee=Eevee("512")),
            SimpleNamespace(eevee=Eevee("64")),
            SimpleNamespace(eevee=Eevee("16")),
            SimpleNamespace(eevee=None),
        ]
        scope = {"bpy": SimpleNamespace(data=SimpleNamespace(scenes=self.scenes))}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "test.py", "exec"), scope)
        self.cap = scope["cap_mobile_eevee_shadow_pool"]

    def test_8gb_ram_no_longer_excludes_shadow_cap(self):
        self.assertEqual(self.cap(16), 2)
        self.assertEqual([s.eevee.shadow_pool_size if s.eevee else None
                          for s in self.scenes], ["16", "16", "16", None])

    def test_is_idempotent_and_does_not_change_data_on_bad_limit(self):
        self.assertEqual(self.cap(16), 2)
        self.assertEqual(self.cap(16), 0)
        self.assertEqual(self.cap(15), 0)

    def test_native_source_patch_dry_run_and_fail_closed(self):
        s = "prefix\n" + patch.OLD + "\nsuffix\n"
        out = patch.patch_source(s)
        self.assertIn("pool_size_mb = min_ii(pool_size_mb, 16);", out)
        self.assertNotIn("total_bytes < (6ull << 30)", out)
        self.assertTrue(out.endswith("\nsuffix\n"))
        for bad in ("", patch.NEW, patch.OLD + patch.OLD):
            with self.assertRaises(ValueError):
                patch.patch_source(bad)

    def test_no_material_ui_or_render_backend_changes(self):
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "cap_mobile_eevee_shadow_pool")
        body = ast.get_source_segment(source, fn)
        self.assertNotIn("bpy.ops.", body)
        self.assertNotIn("use_nodes", body)
        self.assertNotIn("render.engine", body)


if __name__ == "__main__":
    unittest.main()
