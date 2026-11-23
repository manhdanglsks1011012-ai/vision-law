import tempfile,unittest
from unittest.mock import patch
from PyQt6.QtCore import Qt,QSettings
from PyQt6.QtWidgets import QApplication,QMessageBox,QTextBrowser
from PyQt6.QtTest import QTest
from app import Window
from storage import Vault
from trash import move,restore,entries
from reading_view import render_markdown

class TrashReadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_trash_folder_note_restore_and_collision(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);v.create_folder('Luật');a=v.create('A','Luật');b=v.create('B')
            w=Window(d);w.show()
            try:
                w.add_connection(a,b);original=v.read(a)[0];board=w.active_board
                with patch('explorer.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):w.list.trash_item(w.folder_items['Luật'])
                self.assertFalse(v.path(a).exists());self.assertNotIn(a,w.names)
                self.assertIn(a,w.boards.get(board)['positions'])
                item=entries(v)[0];self.assertEqual(item['original'],'Luật')
                w.close_documents();w.save_layout();restore(v,item['id']);w.reload()
                self.assertEqual(v.read(a)[0],original);self.assertIn(a,w.names)
                identity=move(v,b);v.create('B')
                with self.assertRaises(FileExistsError):restore(v,identity)
                self.assertTrue((v.root/entries(v)[0]['stored']).exists())
            finally:
                with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):w.close()
    def test_ctrl_e_preserves_empty_lines_and_source(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');w=Window(d);w.show()
            try:
                w.edit(a);doc=w.documents[a];text='Dòng 1\nDòng 2\n\n\nDòng 5\n'
                doc.input.setPlainText(text);doc.input.setFocus()
                QTest.keyClick(doc.input,Qt.Key.Key_E,Qt.KeyboardModifier.ControlModifier)
                self.assertTrue(doc.source_toggle.isChecked())
                self.assertEqual(doc.preview.toPlainText(),text)
                QTest.keyClick(doc.preview,Qt.Key.Key_E,Qt.KeyboardModifier.ControlModifier)
                self.assertFalse(doc.source_toggle.isChecked());self.assertEqual(doc.input.toPlainText(),text)
                doc.save()
            finally:
                with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):w.close()
