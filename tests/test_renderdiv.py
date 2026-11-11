import unittest
from scripts.patch_blender_elf import OLD, NEW, rewrite


class RenderDivShimTests(unittest.TestCase):
    def test_import_names_same_width(self):
        self.assertEqual(len(OLD), len(NEW))
        self.assertEqual(len(OLD), 21)

    def test_no_patch_on_bad_binary(self):
        with self.assertRaises(Exception):
            rewrite(bytearray(b"not a real ELF file"))

    def test_only_one_property_override(self):
        src = open('native/renderdiv_shim.c', encoding='utf-8').read()
        self.assertIn('"debug.blender.renderdiv"', src)
        self.assertIn("return __system_property_get(name, value);", src)
        self.assertIn("value[0] = '2';", src)


if __name__ == '__main__':
    unittest.main()
