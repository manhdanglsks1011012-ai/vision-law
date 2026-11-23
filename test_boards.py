from portable_refs import strip_references
import tempfile
import unittest
from unittest.mock import patch
from PyQt6.QtCore import QSettings, Qt, QPointF
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from app import Window, Editor
from boards import Boards
from storage import Vault

class IndependentBoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.config.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.config.name)
        cls.app=QApplication.instance() or QApplication([])

    def test_tabs_links_hidden_preview_and_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d); a=v.create('A'); b=v.create('B')
            text,revision=v.read(a); v.save(a,'# A\nNội dung [[B|Liên kết cũ]] cuối.',revision)
            original={n:v.path(n).read_bytes() for n in v.notes()}
            w=Window(d)
            first=w.active_board
            try:
                self.assertEqual(w.connections,[])  # Never import legacy links as edges.
                editor=Editor(w,a)
                self.assertNotIn('Liên kết cũ',editor.preview.toPlainText())
                self.assertNotIn('[[',editor.preview.toPlainText())
                self.assertIn('Nội dung',editor.preview.toPlainText())
                self.assertEqual(editor.input.toPlainText(),v.read(a)[0])
                editor.close()
                w.add_connection(a,b); w.add_connection(a,b)
                self.assertEqual(w.connections,[(a,b)])
                w.board.cards[a].setPos(111,222)
                with patch('app.QInputDialog.getText',return_value=('So sánh',True)):
                    w.new_board()
                second=w.active_board
                w.show(); self.app.processEvents()
                self.assertGreaterEqual(w.tabs.height(),44)
                self.assertFalse(w.board.cards)
                w.add_to_board([a,b]); w.add_connection(b,a)
                w.board.cards[a].setPos(500,600)
                w.tabs.setCurrentIndex(0)
                self.assertEqual(w.active_board,first)
                self.assertEqual(w.board.cards[a].x(),111)
                self.assertEqual(w.connections,[(a,b)])
                w.tabs.setCurrentIndex(1)
                self.assertEqual(w.board.cards[a].x(),500)
                self.assertEqual(w.connections,[(b,a)])
                w.close_tab(1)
                self.assertEqual(len(w.boards.data['boards']),2)
                with patch('app.QInputDialog.getItem',return_value=('2. So sánh',True)):
                    w.open_board()
                self.assertEqual(w.active_board,second)
                w.remove_connection((b,a))
                w.remove_from_board(b)
                self.assertTrue(v.path(b).exists())
            finally:
                w.close()
            reopened=Window(d)
            try:
                self.assertEqual(reopened.active_board,second)
                self.assertNotIn(b,reopened.board.cards)
                self.assertEqual(reopened.connections,[])
                self.assertEqual(reopened.board.cards[a].x(),500)
                self.assertEqual({n:strip_references(v.read(n)[0]).encode() for n in v.notes()},original)
                self.assertEqual(Boards(v).get(first)['edges'],[[a,b]])
            finally: reopened.close()

    def test_drag_ports_and_rename_updates_all_boards(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d); a=v.create('A'); b=v.create('B')
            w=Window(d)
            try:
                w.show(); self.app.processEvents(); w.fit()
                viewport=w.board.viewport()
                start=w.board.mapFromScene(w.board.cards[a].mapToScene(QPointF(260,52)))
                end=w.board.mapFromScene(w.board.cards[b].mapToScene(QPointF(0,52)))
                QTest.mousePress(viewport,Qt.MouseButton.LeftButton,pos=start)
                QTest.mouseMove(viewport,end,30)
                QTest.mouseRelease(viewport,Qt.MouseButton.LeftButton,pos=end)
                self.assertEqual(w.connections,[(a,b)])
                first=w.active_board
                with patch('app.QInputDialog.getText',return_value=('Other',True)): w.new_board()
                w.add_to_board([a,b]); w.add_connection(b,a)
                w.list.relocate(a,'Renamed.md')
                for board in w.boards.data['boards']:
                    self.assertIn('Renamed.md',board['positions'])
                    self.assertNotIn(a,board['positions'])
                    self.assertTrue(any('Renamed.md' in edge for edge in board['edges']))
            finally: w.close()
