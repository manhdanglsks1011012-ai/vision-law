import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtCore import Qt
from storage import Vault
import test_sidebar
from app import Window

class RelocationTests(unittest.TestCase):
    def test_move_folder_rewrites_incoming_outgoing_links_and_positions(self):
        with tempfile.TemporaryDirectory() as directory:
            v=Vault(directory)
            v.create_folder('Luật'); v.create_folder('Khác')
            a=v.create('A','Luật'); b=v.create('B','Luật'); c=v.create('C')
            text,rev=v.read(a); v.save(a,'[[B#Điều 1|xem B]]\n[[C]]',rev)
            text,rev=v.read(c); v.save(c,'[[Luật/A|xem A]]',rev)
            v.save_layout({a:[21,34],b:[3,4]})
            v.relocate('Luật','Khác/Luật')
            self.assertEqual(v.read('Khác/Luật/A.md')[0],'[[Khác/Luật/B#Điều 1|xem B]]\n[[C]]')
            self.assertEqual(v.read(c)[0],'[[Khác/Luật/A|xem A]]')
            self.assertEqual(v.layout()['Khác/Luật/A.md'],[21,34])
            self.assertFalse((v.root/'Luật').exists())
            with self.assertRaises(ValueError): v.relocate('Khác','Khác/Luật/Bad')
            with self.assertRaises(ValueError): v.relocate('Khác/Luật/A.md','Khác/Luật/B.md')

    def test_failure_rolls_back_files(self):
        with tempfile.TemporaryDirectory() as directory:
            v=Vault(directory); a=v.create('A'); b=v.create('B'); v.connect(a,b)
            original=v.read(a)[0]
            with patch.object(v,'save_layout',side_effect=OSError('test disk error')):
                with self.assertRaises(OSError): v.relocate(b,'C.md')
            self.assertTrue(v.path(b).exists())
            self.assertFalse(v.path('C.md').exists())
            self.assertEqual(v.read(a)[0],original)

class ExplorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_sidebar.SidebarTests.setUpClass()
        cls.app = test_sidebar.SidebarTests.app
    def test_sort_expand_remember_and_relocate(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d); v.create_folder('Z'); v.create_folder('A'); n=v.create('First')
            w=Window(d)
            try:
                self.assertEqual(w.list.topLevelItem(0).text(0),'A')
                self.assertEqual(w.list.topLevelItem(1).text(0),'Z')
                w.folder_items['A'].setExpanded(True)
                w.reload()
                self.assertTrue(w.folder_items['A'].isExpanded())
                self.assertFalse(w.folder_items['Z'].isExpanded())
                with patch.object(w,'focus') as focus:
                    w.list.activate(w.tree_items[n],0)
                    focus.assert_called_once_with(n)
                w.board.cards[n].setPos(99,88)
                w.list.relocate(n,'A/First.md')
                self.assertIn('A/First.md',w.names)
                self.assertEqual(w.board.cards['A/First.md'].x(),99)
            finally: w.close()
