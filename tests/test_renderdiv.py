import unittest
from pathlib import Path
from scripts.patch_blender_elf import OLD, NEW, POLL_OLD, POLL_NEW, IMPORTS, rewrite


class RenderDivShimTests(unittest.TestCase):
    def test_native_import_widths(self):
        self.assertEqual(len(OLD), len(NEW))
        self.assertEqual(len(POLL_OLD), len(POLL_NEW))
        self.assertEqual(len(IMPORTS), 2)

    def test_no_patch_on_bad_binary(self):
        with self.assertRaises(Exception):
            rewrite(bytearray(b"invalid ELF"))

    def test_render_scale_is_scoped(self):
        s = Path("native/renderdiv_shim.c").read_text()
        self.assertIn('"debug.blender.renderdiv"', s)
        self.assertIn("return __system_property_get(name, value);", s)
        self.assertIn("value[0] = '2';", s)

    def test_idle_poll_preserves_normal_timeouts(self):
        s = Path("native/renderdiv_shim.c").read_text()
        self.assertIn("if (timeoutMillis == 0)", s)
        self.assertIn("int effective = timeoutMillis;", s)
        self.assertIn("effective = now - last_event_ms < 800 ? 10 : 24;", s)
        self.assertIn("ALooper_pollOnce(effective, outFd, outEvents, outData)", s)
        self.assertIn("static _Thread_local uint64_t last_event_ms;", s)


if __name__ == "__main__":
    unittest.main()
