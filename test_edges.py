from portable_refs import strip_references
import tempfile
import unittest
from PyQt6.QtCore import Qt,QSettings,QPointF
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from app import Window,Card
from storage import Vault
from card_visuals import COLORS, orthogonal_path

class EdgeInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])

    def test_only_axis_aligned_segments_and_labels_opposite_sides(self):
        from card_visuals import Pipe
        from types import SimpleNamespace
        for start,end,side in [(QPointF(0,0),QPointF(300,150),'right'),(QPointF(0,0),QPointF(300,-150),'top'),(QPointF(0,0),QPointF(300,0),'right'),(QPointF(0,0),QPointF(0,150),'bottom')]:
            path=orthogonal_path(start,end,side)
            for i in range(1,path.elementCount()):
                a,b=path.elementAt(i-1),path.elementAt(i)
                self.assertTrue(a.x==b.x or a.y==b.y)
            pipe=Pipe(path,COLORS[0],SimpleNamespace(flow_phase=0),'hello')
            horizontals=[path.elementAt(i).y for i in range(1,path.elementCount()) if path.elementAt(i).y==path.elementAt(i-1).y]
            anchor=horizontals[0] if horizontals else max(start.y(),end.y())
            self.assertLess(pipe.label_rect().bottom(),anchor)
            pipe.note="hello"
            self.assertGreater(pipe.note_rect().top(),anchor)
            self.assertTrue(pipe.boundingRect().contains(pipe.note_rect()))

    def test_two_click_connection_edit_and_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B')
            original={n:v.path(n).read_bytes() for n in v.notes()}
            w=Window(d)
            try:
                w.board.cards[b].setPos(450,180)
                w.show();self.app.processEvents();w.fit()
                board=w.board;viewport=board.viewport()
                start=board.mapFromScene(board.cards[a].mapToScene(Card.PORTS['right']))
                end=board.mapFromScene(board.cards[b].mapToScene(Card.PORTS['left']))
                QTest.mouseMove(viewport,start);self.app.processEvents()
                self.assertEqual(board.cards[a].hover_port,'right')
                QTest.mouseClick(viewport,Qt.MouseButton.LeftButton,pos=start)
                self.assertEqual(board.connecting,a)
                QTest.mouseMove(viewport,end,30)
                self.assertIsNotNone(board.connection_preview)
                QTest.mouseClick(viewport,Qt.MouseButton.LeftButton,pos=end)
                self.assertIsNone(board.connecting)
                self.assertEqual(w.connections,[(a,b)])
                self.assertEqual(board.edges[0].path().elementCount(),3)
                mid=board.mapFromScene(board.edges[0].path().pointAtPercent(0.5))
                QTest.mouseClick(viewport,Qt.MouseButton.LeftButton,pos=mid)
                QTest.qWait(QApplication.doubleClickInterval()+40)
                editor=board.edge_editor
                self.assertIsNotNone(editor)
                editor.label_field.setText('Làm rõ điều kiện áp dụng')
                editor.show_note_field.setChecked(True)
                editor.category_fields['explanation'].setChecked(True)
                editor.routing_field.setCurrentIndex(editor.routing_field.findData('circuit'))
                editor.chosen['color']=COLORS[5];editor.commit()
                edge=board.edges[0]
                self.assertEqual(edge.label,'Giải thích')
                self.assertEqual(edge.note,'Làm rõ điều kiện áp dụng')
                self.assertEqual(edge.color.name(),COLORS[5])
                self.assertGreater(edge.path().elementCount(),2)
                # Escape cancels a click-to-connect without adding an edge.
                QTest.mouseClick(viewport,Qt.MouseButton.LeftButton,pos=start)
                QTest.keyClick(viewport,Qt.Key.Key_Escape)
                self.assertIsNone(board.connecting)
                self.assertEqual(len(board.edges),1)
                QTest.mouseClick(viewport,Qt.MouseButton.LeftButton,pos=start)
                blank=board.mapFromScene(QPointF(-150,-180))
                QTest.mouseMove(viewport,blank,30)
                self.assertIsNotNone(board.connection_preview)
                QTest.mouseClick(viewport,Qt.MouseButton.LeftButton,pos=blank)
                self.assertIsNone(board.connecting)
                self.assertIsNone(board.connection_preview)
                self.assertEqual(len(board.edges),1)
                w.list.relocate(a,'New.md')
                self.assertIn('New.md\n'+b,w.boards.get(w.active_board)['edge_styles'])
            finally:w.close()
            reopened=Window(d)
            try:
                self.assertEqual(reopened.board.edges[0].label,'Giải thích')
                self.assertEqual(reopened.board.edges[0].note,'Làm rõ điều kiện áp dụng')
                self.assertEqual(reopened.board.edges[0].color.name(),COLORS[5])
                self.assertEqual(strip_references(v.read('New.md')[0]).encode(),original[a])
                self.assertEqual(v.path(b).read_bytes(),original[b])
            finally:reopened.close()
