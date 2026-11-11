import unittest
from pathlib import Path

class FullBufferModeTests(unittest.TestCase):
    def test_renderdiv_compiles_both_variants(self):
        c = Path('native/renderdiv_shim.c').read_text()
        sh = Path('scripts/install_renderdiv.sh').read_text()
        workflow = Path('.github/workflows/build.yml').read_text()
        self.assertIn('#if MOBILE_RENDER_DIVISOR == 1', c)
        self.assertIn("value[0] = '1';", c)
        self.assertIn("value[0] = '2';", c)
        self.assertIn('DMOBILE_RENDER_DIVISOR="$render_div"', sh)
        self.assertIn('export ANDROID_BLENDER_RENDERDIV=1', workflow)
        self.assertIn('FULL-buffer-UNVERIFIED.apk', workflow)

if __name__=='__main__':
    unittest.main()
