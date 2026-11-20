"""Offline native source and project-integrity tests. No GPU, APK or device."""
import ast
import importlib.util
import tempfile
from pathlib import Path
import unittest

SOURCE=Path("addon/safe_edit.py").read_text(encoding="utf-8")
spec=importlib.util.spec_from_file_location(
    "mali_native", "scripts/patch_mobile_shadow_pool.py")
patch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


def fixture():
    return "\n".join([
        "#define EXAMPLE_SOURCE 1",
        "  int pool_size_mb = scene.eevee.shadow_pool_size;",
        patch.OLD,
        "  const size_t pool_byte_size = size_t(pool_size_mb) * square_i(1024);",
        ""
    ])


class MaterialBudgetSafetyTests(unittest.TestCase):
    def test_8gb_device_budget_no_longer_depends_on_physical_ram(self):
        for limit in (16, 32, 64):
            result=patch.patch_source(fixture(), limit)
            self.assertIn(f"pool_size_mb = min_ii(pool_size_mb, {limit});", result)
            self.assertNotIn("total_bytes < (6ull << 30)", result)
            self.assertIn("scene.eevee.shadow_pool_size;", result)
            self.assertIn("square_i(1024);", result)

    def test_patch_rejects_wrong_revision_duplicate_and_bad_limit(self):
        source=fixture()
        for s in ("", patch.OLD, source+source,
                  source.replace("shadow_pool_size;", "other;"),
                  patch.patch_source(source)):
            with self.assertRaises(ValueError):
                patch.patch_source(s)
        for n in (-1, 0, 8, 15, 128, "16", True):
            with self.assertRaises(ValueError):
                patch.patch_source(source, n)

    def test_dry_run_never_modifies_checkout(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/patch.RELATIVE_PATH
            file.parent.mkdir(parents=True)
            file.write_text(fixture())
            before=file.read_bytes()
            out=patch.patch_file(td, 16, apply=False)
            self.assertFalse(out["applied"])
            self.assertTrue(out["native_rebuild_required"])
            self.assertEqual(file.read_bytes(), before)
            self.assertFalse(file.with_name(file.name+".pre-mali-budget.bak").exists())

    def test_applied_patch_has_verifiable_backup_and_refuses_repeat(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/patch.RELATIVE_PATH
            file.parent.mkdir(parents=True)
            file.write_text(fixture())
            before=file.read_bytes()
            out=patch.patch_file(td, 16, apply=True)
            backup=file.with_name(file.name+".pre-mali-budget.bak")
            self.assertTrue(out["applied"])
            self.assertEqual(backup.read_bytes(), before)
            self.assertEqual(out["before_sha256"], patch.sha256(before))
            self.assertEqual(out["after_sha256"], patch.sha256(file.read_bytes()))
            with self.assertRaises(ValueError):
                patch.patch_file(td, 16, apply=True)

    def test_project_scenes_not_automatically_mutated(self):
        tree=ast.parse(SOURCE)
        self.assertFalse(any(isinstance(n, ast.FunctionDef)
                             and n.name == "cap_mobile_eevee_shadow_pool"
                             for n in tree.body))
        self.assertNotIn("eevee.shadow_pool_size =", SOURCE)
        self.assertNotIn("bpy.data.materials.new(", SOURCE)
        self.assertNotIn("object.material_slot_add", SOURCE)
        self.assertIn("def apply_low_gpu()", SOURCE)
        self.assertIn("def on_load_post(_unused)", SOURCE)

    def test_source_gate_does_not_claim_gpu_or_material_fix(self):
        self.assertIn("Native GPU synchronization/driver bugs are not fixed", patch.replacement())
        self.assertIn("libblender.so", patch.__doc__)
        self.assertEqual(patch.SUPPORTED_LIMIT_MB, (16,32,64))


if __name__=="__main__":
    unittest.main()
