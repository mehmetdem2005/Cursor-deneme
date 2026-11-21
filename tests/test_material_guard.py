"""Unit tests for pinned Blender UI A/B patch; native GPU is not emulated."""
import runpy
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

guard = runpy.run_path("scripts/patch_material_ui.py")
original = b"""class MATERIAL_PT_preview:
    def draw(self, context):
        self.layout.template_preview(context.material)
classes = (
    MATERIAL_PT_preview,
    EEVEE_MATERIAL_PT_context_material,
)
"""


class MaterialGuardTests(unittest.TestCase):
    def test_only_thumbnail_registration_removed(self):
        result = guard["patch_text"](original)
        self.assertNotIn(b"    MATERIAL_PT_preview,", result)
        self.assertIn(b"    EEVEE_MATERIAL_PT_context_material,", result)
        self.assertIn(b"self.layout.template_preview(context.material)", result)

    def test_fail_closed_when_upstream_changes(self):
        with self.assertRaises(ValueError):
            guard["patch_text"](b"classes = ()")

    def test_zip_preserves_other_entry_and_cannot_double_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "blender_runtime.zip"
            with ZipFile(path, "w") as zf:
                zf.writestr(guard["TARGET"], original)
                zf.writestr("scripts/startup/unrelated.py", b"unchanged")
            guard["patch_archive"](path)
            with ZipFile(path) as zf:
                self.assertEqual(zf.read("scripts/startup/unrelated.py"), b"unchanged")
                self.assertEqual(zf.namelist().count(guard["TARGET"]), 1)
            with self.assertRaises(ValueError):
                guard["patch_archive"](path)
