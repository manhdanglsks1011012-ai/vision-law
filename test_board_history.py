import tempfile,unittest
from PyQt6.QtCore import Qt,QSettings,QPoint,QPointF,QEvent
from PyQt6.QtGui import QWheelEvent,QNativeGestureEvent
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from app import Window
from storage import Vault

class NavigationHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_board_edits_camera_undo_redo_and_editor_undo(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B');w=Window(d);w.show();self.app.processEvents();w.fit();w.board.history.activate()
            try:
                board=w.board;history=board.history;before=history.snapshot()
                board.cards[a].setPos(130,220);w.save_layout();history.commit()
                w.add_connection(a,b);history.commit()
                board.set_style(a,tier=4);history.commit()
                scale=board.transform().m11()
                for _ in range(5):board.set_zoom(board.transform().m11()*1.05)
                history.commit()
                self.assertEqual(len(history.entries[history.key][0]),5)
                board.setFocus();QTest.keyClick(board,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier)
                self.assertAlmostEqual(board.transform().m11(),scale,places=5)
                QTest.keyClick(board,Qt.Key.Key_Y,Qt.KeyboardModifier.ControlModifier)
                self.assertGreater(board.transform().m11(),scale)
                for _ in range(4):history.step(-1)
                self.assertEqual(w.connections,[]);self.assertEqual(board.cards[a].x(),before['data']['positions'][a][0])
                for _ in range(4):history.step(1)
                self.assertEqual(w.connections,[(a,b)]);self.assertEqual(board.cards[a].x(),130)
                self.assertEqual(w.boards.get(w.active_board)['styles'][a]['tier'],4)
                # Swiping pans, rather than changing zoom, at 60% of the delta.
                history.activate();bar=board.verticalScrollBar();y=bar.value();z=board.transform().m11()
                event=QWheelEvent(QPointF(200,200),QPointF(200,200),QPoint(0,100),QPoint(0,0),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
                QApplication.sendEvent(board.viewport(),event)
                self.assertEqual(bar.value(),y-60);self.assertEqual(board.transform().m11(),z)
                history.commit();history.step(-1);self.assertAlmostEqual(bar.value(),y,delta=1)
                w.edit(a);doc=w.documents[a];doc.input.setFocus();doc.input.insertPlainText('test')
                QTest.keyClick(doc.input,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier)
                self.assertNotIn('test',doc.input.toPlainText())
            finally:w.close()
