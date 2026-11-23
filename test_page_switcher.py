import tempfile
import unittest
from unittest.mock import patch
from PyQt6.QtCore import Qt,QSettings
from PyQt6.QtWidgets import QApplication,QMessageBox,QWidget
from PyQt6.QtTest import QTest
from app import Window
from storage import Vault

class PageSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_window_tabs_split_picker_and_focus(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B');c=v.create('C');w=Window(d);w.show()
            try:
                w.edit(a);w.edit(b);self.app.processEvents()
                first,second=w.documents[a],w.documents[b]
                self.assertFalse(first.isWindow());self.assertIs(QWidget.window(first),w)
                group=w.desk.groups[0]
                self.assertEqual(group.left.count(),2)
                self.assertIsNot(QApplication.focusWidget(),second.input)
                original=second.input.toPlainText()
                QTest.keyClick(QApplication.focusWidget(),Qt.Key.Key_Tab)
                self.assertEqual(second.input.toPlainText(),original)
                second.input.setPlainText('Bản nháp')
                group.toggle_split();self.app.processEvents()
                self.assertTrue(group.split_mode);self.assertEqual(group.right.count(),1)
                for document in group.documents():
                    self.assertTrue(document.panels['out'][0].isHidden())
                    self.assertTrue(document.panels['in'][0].isHidden())
                    self.assertFalse(document.panes.isHidden())
                second.input.setFocus();second.input.setPlainText('Bản nháp chia đôi')
                QTest.keyClick(second.input,Qt.Key.Key_S,Qt.KeyboardModifier.ControlModifier)
                self.app.processEvents()
                self.assertEqual(v.read(b)[0],'# B\n\nBản nháp chia đôi')
                second.input.setPlainText('Bản nháp')
                group.toggle_split();self.assertFalse(group.split_mode)
                w.desk.detach(second);self.app.processEvents()
                self.assertEqual(len(w.desk.groups),2)
                new_group=w.desk.locate(second)[0]
                self.assertIsNot(new_group,group)
                w.show_board_page()
                target=w.board
                QTest.keyPress(target,Qt.Key.Key_Tab)
                QTest.keyPress(target,Qt.Key.Key_Space)
                QTest.keyRelease(target,Qt.Key.Key_Space)
                self.assertIsNotNone(w.page_switcher.popup)
                self.assertIsNone(w.current_document)  # selection not committed yet
                self.assertEqual(w.page_switcher.list.count(),3)
                QTest.keyRelease(target,Qt.Key.Key_Tab)
                self.assertIsNone(w.page_switcher.popup)
                self.assertEqual(w.current_document,b)  # MRU window, not creation order
                self.assertEqual(second.input.toPlainText(),'Bản nháp')
                self.assertIsNot(QApplication.focusWidget(),second.input)
                # Explicitly editing permits a normal Tab indentation.
                second.input.setFocus();QTest.keyClick(second.input,Qt.Key.Key_Tab)
                self.assertEqual(second.input.toPlainText(),'    Bản nháp')
                # Transfer to another window retains the same editor instance and draft.
                w.desk.move_document(second,group.left)
                self.assertIs(group.left.widget(group.left.indexOf(second)),second)
                self.assertEqual(second.input.toPlainText(),'    Bản nháp')
                self.assertEqual(len(w.desk.groups),1)
                self.assertTrue(second.save());second.close();first.close()
                self.assertFalse(w.documents);self.assertFalse(w.desk.area.isVisible())
            finally:
                with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):w.close()

    def test_picker_escape_and_close_cancel_keep_drafts(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');w=Window(d);w.show()
            try:
                w.edit(a);doc=w.documents[a];doc.input.setPlainText('draft')
                w.page_switcher.advance();self.assertIsNotNone(w.page_switcher.popup)
                QTest.keyClick(doc,Qt.Key.Key_Escape)
                self.assertIsNone(w.page_switcher.popup);self.assertIn(a,w.documents)
                group=w.desk.locate(doc)[0]
                with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel):
                    self.assertFalse(group.sub.close())
                self.assertIn(a,w.documents);self.assertEqual(doc.input.toPlainText(),'draft')
            finally:
                with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):w.close()
