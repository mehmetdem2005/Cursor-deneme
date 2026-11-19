"""Offline mocked regression tests for v33 Material Guard. No real GPU is tested."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE = Path("addon/safe_edit.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


class FakeMat:
    def __init__(self, name):
        self.name, self.use_nodes, self.diffuse_color = name, True, None


class FakeMaterials:
    def __init__(self):
        self.created = []

    def new(self, name):
        item = FakeMat(name)
        self.created.append(item)
        return item


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.mats = FakeMaterials()
        props = SimpleNamespace(context="MATERIAL")
        self.prop = SimpleNamespace(type="PROPERTIES", spaces=SimpleNamespace(active=props))
        self.obj = SimpleNamespace(type="MESH", data=SimpleNamespace(materials=[]), active_material_index=-1)
        self.ctx = SimpleNamespace(mode="OBJECT", active_object=self.obj,
                                   screen=SimpleNamespace(areas=[self.prop]))
        names = {"create_safe_material", "material_guard_log"}
        code = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in names]
        self.events = []
        self.scope = {
            "bpy": SimpleNamespace(data=SimpleNamespace(materials=self.mats)),
            "apply_paint_profile": lambda context, textured=False: 1,
        }
        exec(compile(ast.Module(body=code, type_ignores=[]),
                     "safe_material_test.py", "exec"), self.scope)
        self.scope["material_guard_log"] = self.events.append

    def test_proton_material_created_without_nodes_or_preview(self):
        self.assertTrue(self.scope["create_safe_material"](self.ctx, "PROTON"))
        mat = self.obj.data.materials[0]
        self.assertEqual(self.mats.created, [mat])
        self.assertFalse(mat.use_nodes)
        self.assertEqual(mat.diffuse_color, (0.03, 0.26, 0.90, 1.0))
        self.assertEqual(self.obj.active_material_index, 0)
        self.assertEqual(self.prop.spaces.active.context, "OBJECT")
        self.assertEqual(self.events[-1], "ASSIGNED")

    def test_neutron_material(self):
        self.assertTrue(self.scope["create_safe_material"](self.ctx, "NEUTRON"))
        self.assertEqual(self.obj.data.materials[0].diffuse_color,
                         (0.32, 0.10, 0.65, 1.0))

    def test_never_changes_data_in_edit_or_paint_mode(self):
        for mode in ("EDIT_MESH", "PAINT_TEXTURE", "PAINT_WEIGHT", "POSE", "SCULPT"):
            self.ctx.mode = mode
            self.assertFalse(self.scope["create_safe_material"](self.ctx, "PROTON"))
        self.assertEqual(self.mats.created, [])
        self.assertEqual(self.prop.spaces.active.context, "MATERIAL")

    def test_no_operation_with_wrong_selection_or_preset(self):
        self.obj.type = "CURVE"
        self.assertFalse(self.scope["create_safe_material"](self.ctx, "PROTON"))
        self.obj.type = "MESH"
        self.assertFalse(self.scope["create_safe_material"](self.ctx, "UNKNOWN"))
        self.assertEqual(self.mats.created, [])

    def test_no_gpu_preview_node_or_mode_calls(self):
        segment = next(ast.get_source_segment(SOURCE, n) for n in TREE.body
                       if isinstance(n, ast.FunctionDef) and n.name == "create_safe_material")
        for forbidden in ("bpy.ops.material.new", "bpy.ops.object.mode_set",
                          "use_nodes = True", "type = 'MATERIAL'", "bpy.ops.render",
                          "bpy.ops.paint"):
            self.assertNotIn(forbidden, segment)
        self.assertIn("mat.use_nodes = False", segment)
        self.assertIn("material_guard_log('BEFORE_NEW')", segment)


if __name__ == "__main__":
    unittest.main()
