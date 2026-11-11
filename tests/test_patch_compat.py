import tempfile
from pathlib import Path
import unittest

from scripts.patch_compat import patch_smali


EXAMPLE = """\
.class public Lorg/blender/blender/BlenderActivity;
.method protected onCreate(Landroid/os/Bundle;)V
    .locals 1
    return-void
.end method
.method private publishHardwareNames()V
    .locals 2
    sget-object v0, Landroid/os/Build;->SOC_MANUFACTURER:Ljava/lang/String;
    sget-object v1, Landroid/os/Build;->SOC_MODEL:Ljava/lang/String;
    return-void
.end method
"""


class CompatPatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.target = self.dir / "smali/org/blender/blender/BlenderActivity.smali"
        self.target.parent.mkdir(parents=True)
        self.target.write_text(EXAMPLE, encoding="utf-8")

    def test_replaces_only_unsupported_soc_fields(self):
        patch_smali(self.dir)
        text = self.target.read_text()
        self.assertIn("Landroid/os/Build;->MANUFACTURER:Ljava/lang/String;", text)
        self.assertIn("Landroid/os/Build;->HARDWARE:Ljava/lang/String;", text)
        self.assertNotIn("SOC_MODEL:", text)
        self.assertNotIn("SOC_MANUFACTURER:", text)

    def test_fails_closed_on_unexpected_upstream(self):
        self.target.write_text(EXAMPLE.replace("SOC_MODEL", "MODEL"))
        with self.assertRaisesRegex(RuntimeError, "Expected one"):
            patch_smali(self.dir)


if __name__ == "__main__":
    unittest.main()
