"""Check no-audio launch flag is injected before native activity startup."""
import runpy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

s=runpy.run_path("scripts/patch_audio_launch.py")
STUB=""".method protected onCreate(Landroid/os/Bundle;)V
    invoke-direct {p0}, Lorg/blender/blender/BlenderActivity;->publishLaunchFile(Landroid/content/Intent;)V
    invoke-super {p0, p1}, Landroid/app/NativeActivity;->onCreate(Landroid/os/Bundle;)V
.end method
"""

class TestAudioStartup(unittest.TestCase):
    def test_launch_flag_precedes_native(self):
        patched=s["inject"](STUB)
        self.assertLess(patched.index(s["CALL"]),patched.index(s["SUPER"]))
        self.assertIn('const-string v4, "-noaudio\\n"',patched)
        self.assertIn('blender_args.txt',patched)
        self.assertIn('Ljava/io/File;->exists()Z',patched)
        self.assertIn('.catch Ljava/lang/Exception;',patched)
    def test_rejects_unexpected_and_double_patch(self):
        with self.assertRaises(ValueError):s["inject"]("garbage")
        with self.assertRaises(ValueError):s["inject"](s["inject"](STUB))
    def test_on_disk(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"smali/org/blender/blender/BlenderActivity.smali"
            p.parent.mkdir(parents=True)
            p.write_text(STUB)
            s["apply"](d)
            self.assertIn("initSafeAudioArgs",p.read_text())
