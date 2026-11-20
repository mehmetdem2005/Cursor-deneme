"""Read-only source risk scanner tests."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

spec=importlib.util.spec_from_file_location("scan","scripts/scan_android_material_risks.py")
scanner=importlib.util.module_from_spec(spec)
# scanner imports patch_mobile_shadow_pool from scripts/ -- add module path explicitly
import sys
sys.path.insert(0,str(Path("scripts").resolve()))
spec.loader.exec_module(scanner)


class ScanTests(unittest.TestCase):
    def test_scanner_reports_legacy_without_claiming_safety(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            for p in (scanner.RELATIVE_PATH,scanner.PREVIEW_FILE,scanner.RESOURCE_FILE):
                (root/p).parent.mkdir(parents=True,exist_ok=True)
            (root/scanner.RELATIVE_PATH).write_text(
                "  int pool_size_mb = scene.eevee.shadow_pool_size;\n"+scanner.OLD)
            (root/scanner.PREVIEW_FILE).write_text(
                'object.material_slot_add\nnew="material.new"\nMATERIAL_PT_preview,')
            (root/scanner.RESOURCE_FILE).write_text("discard_framebuffers_for_view(")
            state=scanner.inspect(td)
            self.assertTrue(state["old_6_gib_shadow_gate"])
            self.assertTrue(state["standard_material_add_preserved"])
            self.assertTrue(state["eevee_preview_panel"])
            self.assertTrue(state["legacy_framebuffer_discard_api"])
            self.assertFalse(state["safe_to_install"])
            self.assertEqual(len(state["issues"]),3)
            (root/scanner.RELATIVE_PATH).write_text("no gate")
            state=scanner.inspect(td)
            self.assertFalse(state["old_6_gib_shadow_gate"])
            self.assertEqual(len(state["issues"]),2)

if __name__=="__main__":
    unittest.main()
