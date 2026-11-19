"""General v33 Material UI patch tests. These do not test the physical Mali GPU."""
import ast
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import unittest

SRC = Path("scripts/patch_material_ui.py").read_text(encoding="utf-8")
OPS = Path("addon/safe_edit.py").read_text(encoding="utf-8")
spec = importlib.util.spec_from_file_location("patch_material_ui", "scripts/patch_material_ui.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Mat:
    def __init__(self, name):
        self.name = name

    def copy(self):
        return Mat(self.name + '.001')


class SlotCollection(list):
    def append(self, obj):
        super().append(SimpleNamespace(material=obj))


class MaterialsData(list):
    def __init__(self, obj):
        self.obj = obj

    def append(self, mat):
        self.obj.material_slots.append(SimpleNamespace(material=mat))

    def __len__(self):
        return len(self.obj.material_slots)


class Tests(unittest.TestCase):
    def test_standard_material_panel_is_integrated(self):
        source = (
            "class MATERIAL_PT_preview: pass\n"
            "class EEVEE_MATERIAL_PT_surface: pass\n"
            "class MATERIAL_PT_viewport: pass\n"
            "class MATERIAL_UL_matslots: pass\n"
            "col.operator(\"object.material_slot_add\", icon='ADD', text=\"\")\n"
            "row.template_ID(ob, \"active_material\", new=\"material.new\")\n"
            "classes = (\n    MATERIAL_PT_preview,\n    MATERIAL_PT_viewport,\n)\n"
        )
        out = mod.patch_material_source(source)
        self.assertIn('col.operator("wm.material_ui_slot_add"', out)
        self.assertIn('new="wm.material_ui_new"', out)
        self.assertNotIn("    MATERIAL_PT_preview,\n", out)
        self.assertIn("MATERIAL_PT_viewport", out)
        self.assertIn("EEVEE_MATERIAL_PT_surface", out)
        with self.assertRaises(ValueError):
            mod.patch_material_source(out)

    def test_bpy_operator_guards_and_no_preset(self):
        tree = ast.parse(OPS)
        required = {"material_ui_eligible", "material_ui_log"}
        cls_required = {"WM_OT_material_ui_new", "WM_OT_material_ui_slot_add"}
        found = {x.name for x in tree.body if isinstance(x, ast.ClassDef)}
        self.assertTrue(cls_required <= found)
        code = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name in required]
        self.assertEqual(len(code), 2)
        self.assertNotIn('PROTON', ast.get_source_segment(OPS, next(
            n for n in tree.body if isinstance(n, ast.ClassDef)
            and n.name == "WM_OT_material_ui_new")))
        self.assertIn("obj.data.materials.append(None)", OPS)
        self.assertIn("bpy.data.materials.new(name='Material')", OPS)


if __name__ == "__main__":
    unittest.main()
