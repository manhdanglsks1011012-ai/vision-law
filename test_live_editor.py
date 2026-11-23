import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest
from live_editor import LiveEditor

class LiveEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_shortcuts_lists_and_undo(self):
        editor=LiveEditor('hello');editor.selectAll()
        QTest.keyClick(editor,Qt.Key.Key_B,Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(editor.toPlainText(),'**hello**')
        editor.undo();self.assertEqual(editor.toPlainText(),'hello')
        editor.heading(2);self.assertEqual(editor.toPlainText(),'## hello')
        editor.setPlainText('1. First');editor.moveCursor(QTextCursor.MoveOperation.End)
        QTest.keyClick(editor,Qt.Key.Key_Return)
        self.assertEqual(editor.toPlainText(),'1. First\n2. ')
        QTest.keyClick(editor,Qt.Key.Key_Return)
        self.assertEqual(editor.toPlainText(),'1. First\n')
        editor.setPlainText('- [x] Done');editor.moveCursor(QTextCursor.MoveOperation.End)
        QTest.keyClick(editor,Qt.Key.Key_Return)
        self.assertEqual(editor.toPlainText(),'- [x] Done\n- [ ] ')
        editor.close()

    def test_underline_and_nested_list_indentation_roundtrip(self):
        editor=LiveEditor('Nội dung');editor.selectAll();editor.wrap('<u>')
        self.assertEqual(editor.toPlainText(),'<u>Nội dung</u>')
        editor.selectAll();editor.wrap('<u>');self.assertEqual(editor.toPlainText(),'Nội dung')
        editor.setPlainText('- A\n- B');editor.selectAll()
        QTest.keyClick(editor,Qt.Key.Key_Tab)
        self.assertEqual(editor.toPlainText(),'    - A\n    - B')
        editor.selectAll();QTest.keyClick(editor,Qt.Key.Key_Backtab)
        self.assertEqual(editor.toPlainText(),'- A\n- B')
        editor.undo();self.assertEqual(editor.toPlainText(),'    - A\n    - B')
        editor.close()
