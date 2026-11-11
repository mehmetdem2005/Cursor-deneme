import ast
import json
import struct
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'addon/mobile_speed.py'
SRC = PATH.read_text()
MODULE = ast.parse(SRC)
FUNCTION = next(n for n in MODULE.body if isinstance(n, ast.FunctionDef)
                and n.name == '_mobile_scan_glb')
CODE = compile(ast.Module(body=[FUNCTION], type_ignores=[]), str(PATH), 'exec')
NS = {}
exec(CODE, NS)
scan = NS['_mobile_scan_glb']

def make_glb(d):
    raw = json.dumps(d).encode('utf-8')
    raw += b' ' * (-len(raw) % 4)
    return struct.pack('<4sII', b'glTF', 2, 20 + len(raw)) + (
        struct.pack('<I4s', len(raw), b'JSON') + raw)

class GLBPreflightTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'test.glb'
        self.doc = {'asset': {'version': '2.0'},
                    'accessors': [{'count': 54}],
                    'meshes': [{'primitives': [{'attributes': {'POSITION': 0}}]}]}
    def put(self):
        self.path.write_bytes(make_glb(self.doc))
    def test_valid_glb(self):
        self.put()
        self.assertEqual(scan(self.path)['vertices'], 54)
    def test_invalid_header(self):
        self.put()
        data = bytearray(self.path.read_bytes())
        data[8:12] = struct.pack('<I', 4)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'header'):
            scan(self.path)
    def test_draco_detected(self):
        self.doc['meshes'][0]['primitives'][0]['extensions'] = {
            'KHR_draco_mesh_compression': {}}
        self.put()
        self.assertTrue(scan(self.path)['draco'])
    def test_meshopt_detected(self):
        self.doc['bufferViews'] = [{'extensions': {'EXT_meshopt_compression': {}}}]
        self.put()
        self.assertTrue(scan(self.path)['meshopt'])
    def test_ktx2_detected(self):
        self.doc['images'] = [{'mimeType': 'image/ktx2'}]
        self.put()
        self.assertTrue(scan(self.path)['basis'])
    def test_large_mesh_requires_override(self):
        self.doc['accessors'][0]['count'] = 2000000
        self.put()
        self.assertTrue(scan(self.path)['heavy'])
    def test_gltf_json(self):
        path = self.path.with_suffix('.gltf')
        path.write_text(json.dumps(self.doc))
        self.assertEqual(scan(path)['vertices'], 54)
    def test_invalid_accessor(self):
        self.doc['meshes'][0]['primitives'][0]['attributes']['POSITION'] = 4
        self.put()
        with self.assertRaisesRegex(ValueError, 'accessor'):
            scan(self.path)

if __name__ == '__main__':
    unittest.main()
