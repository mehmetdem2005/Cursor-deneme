"""Offline native EEVEE patch regression tests (never executes ARM instructions)."""
import ast
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("native_budget","scripts/patch_native_mali_shadow_elf.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class BinarySafetyTests(unittest.TestCase):
    def test_budget_instruction_and_neighbor_guards(self):
        self.assertEqual(mod.CODE_ADDR,0x27D817C)
        self.assertEqual(mod.NOP,bytes.fromhex("1f2003d5"))
        self.assertEqual(mod.NEIGHBORS[0x27D813C],("cmp","w23, #0x10"))
        self.assertEqual(mod.NEIGHBORS[mod.CODE_ADDR],("csel","w9, w9, w23, gt"))
        self.assertEqual(len(mod.NEIGHBORS),10)

    def test_arm64_machine_no_op_valid(self):
        self.assertEqual(mod.decode_one(mod.NOP,mod.CODE_ADDR,0),("nop",""))

    def test_declines_non_elf_and_empty_binary(self):
        for value in (b"",b"another app",b"PK"+b"\x00"*96):
            with self.assertRaises((ValueError,Exception)):
                mod.patch_blob(value)

    def test_no_unsigned_partial_patching(self):
        source=Path("scripts/patch_native_mali_shadow_elf.py").read_text()
        self.assertIn("read_instructions(result,True)",source)
        self.assertIn("if result[:old_offset]!=original[:old_offset]",source)
        self.assertIn('raise ValueError("Two sysconf calls',source)
        self.assertIn('os.replace(temp,path)',source)

if __name__=="__main__":unittest.main()
