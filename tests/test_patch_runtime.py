import tempfile
from pathlib import Path
from zipfile import ZipFile
import unittest

from scripts.patch_runtime import install, ENTRY


class RuntimePatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.archive = self.dir / "assets/blender_runtime.zip"
        self.archive.parent.mkdir(parents=True)
        self.script = self.dir / "mobile_speed.py"
        self.script.write_text("def register():\n    return True\n")
        with ZipFile(self.archive, "w") as z:
            z.writestr("scripts/startup/bl_ui/__init__.py", b"original")
            z.writestr("scripts/modules/bpy/utils/__init__.py", b"original bpy")

    def test_appends_without_mutating_original_content(self):
        install(self.dir, self.script)
        with ZipFile(self.archive) as z:
            self.assertEqual(z.read(ENTRY), self.script.read_bytes())
            self.assertEqual(z.read("scripts/startup/bl_ui/__init__.py"), b"original")
            self.assertEqual(len(z.namelist()), 3)

    def test_abort_if_already_modified(self):
        install(self.dir, self.script)
        with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
            install(self.dir, self.script)

    def test_abort_if_no_blender_startup(self):
        with ZipFile(self.archive, "w") as z:
            z.writestr("not_blender.txt", "x")
        with self.assertRaisesRegex(ValueError, "scripts/startup"):
            install(self.dir, self.script)


if __name__ == "__main__":
    unittest.main()
