import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import unittest
from scripts.package_dual_apk import (
    OLD_NAME, NEW_NAME, package, file_sha256, OLD_SHA256
)


class DualPackageTests(unittest.TestCase):
    def test_byte_for_byte_and_hashes(self):
        with TemporaryDirectory() as d:
            directory = Path(d)
            old, new, target = (directory/'old.apk', directory/'new.apk',
                                directory/'final.zip')
            old.write_bytes(b'old apk test fixture')
            new.write_bytes(b'new apk test fixture')
            old_sha = file_sha256(old)
            self.assertEqual(package(old, new, target, old_sha,
                                     old.stat().st_size)[0], old_sha)
            with ZipFile(target) as z:
                self.assertEqual(z.read(OLD_NAME), old.read_bytes())
                self.assertEqual(z.read(NEW_NAME), new.read_bytes())
                self.assertIn(old_sha, z.read('SHA256SUMS.txt').decode())
                self.assertIsNone(z.testzip())

    def test_rejects_wrong_original(self):
        with TemporaryDirectory() as d:
            old, new, target = [Path(d)/n for n in ('old.apk','new.apk','x.zip')]
            old.write_bytes(b'wrong'); new.write_bytes(b'other')
            with self.assertRaisesRegex(ValueError, 'SHA256'):
                package(old, new, target, OLD_SHA256, 5)
            self.assertFalse(target.exists())

    def test_rejects_same_apk(self):
        with TemporaryDirectory() as d:
            old, new, target = [Path(d)/n for n in ('old.apk','new.apk','x.zip')]
            old.write_bytes(b'identical'); new.write_bytes(b'identical')
            with self.assertRaisesRegex(ValueError, 'identical'):
                package(old, new, target, file_sha256(old), 9)


if __name__ == '__main__':
    unittest.main()
