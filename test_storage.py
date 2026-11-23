import tempfile
import unittest
from pathlib import Path
from storage import Vault, ConflictError

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.v = Vault(self.tmp.name)

    def test_roundtrip_backup_conflict(self):
        name = self.v.create('Nghĩa vụ')
        old, rev = self.v.read(name)
        self.v.save(name, 'Nội dung mới\n', rev)
        self.assertEqual((self.v.root / '.vision-law/backups' / name).read_text(), old)
        with self.assertRaises(ConflictError):
            self.v.save(name, 'Không được ghi đè', rev)
        self.assertEqual(self.v.read(name)[0], 'Nội dung mới\n')

    def test_link_roundtrip_and_no_duplicates(self):
        a, b = self.v.create('Nghĩa vụ'), self.v.create('Tài sản')
        self.v.connect(a, b)
        self.v.connect(a, b)
        self.assertEqual(self.v.links(a), ['Tài sản'])
        self.assertEqual(self.v.resolve('Tài sản', a, self.v.notes()), b)
        self.v.save_layout({a: [-20, 310]})
        self.assertEqual(Vault(self.v.root).layout(), {a: [-20, 310]})

    def test_paths_existing_files_and_ambiguous_links(self):
        with self.assertRaises(ValueError):
            self.v.path('../outside.md')
        self.v.create('A')
        with self.assertRaises(FileExistsError):
            self.v.create('A')
        for folder in ('one', 'two'):
            (self.v.root / folder).mkdir()
            (self.v.root / folder / 'B.md').write_text('B')
        self.assertIsNone(self.v.resolve('B', 'A.md', self.v.notes()))
        self.assertEqual(self.v.resolve('B', 'one/C.md', self.v.notes()), 'one/B.md')

if __name__ == '__main__':
    unittest.main()
