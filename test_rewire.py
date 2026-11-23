from portable_refs import strip_references
import tempfile,unittest
from PyQt6.QtCore import Qt,QSettings,QPointF
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from app import Window,Card
from storage import Vault
from boards import Boards

class RewireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_rewire_one_of_two_incoming_and_cancel(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B');c=v.create('C');w=Window(d);w.show()
            original={n:v.path(n).read_bytes() for n in v.notes()}
            try:
                board=w.board;board.cards[a].setPos(0,0);board.cards[b].setPos(550,0);board.cards[c].setPos(0,250)
                w.add_connection(a,b,'right','left');w.add_connection(c,b,'right','left')
                key=a+'\n'+b;data=w.boards.get(w.active_board)
                data.setdefault('edge_styles',{})[key]={'label':'Giữ tên','color':'#ef3344'};w.boards.save()
                w.fit();self.app.processEvents()
                # Grab the pipe just before it reaches the target, away from the +.
                start=board.mapFromScene(board.cards[b].mapToScene(Card.PORTS['left'])+QPointF(-45,0))
                end=board.mapFromScene(board.cards[b].mapToScene(Card.PORTS['bottom']))
                QTest.mousePress(board.viewport(),Qt.MouseButton.LeftButton,pos=start)
                QTest.mouseMove(board.viewport(),end,30)
                self.assertIsNotNone(board.rewiring)
                QTest.mouseRelease(board.viewport(),Qt.MouseButton.LeftButton,pos=end)
                self.assertIsNone(board.rewiring)
                self.assertEqual(data['ports'][key]['target'],'bottom')
                self.assertEqual(data['ports'][c+'\n'+b]['target'],'left')
                self.assertEqual(len(w.connections),2)
                self.assertEqual(data['edge_styles'][key],{'label':'Giữ tên','color':'#ef3344'})
                # Dropping on empty space keeps a pending preview; clicking there cancels.
                board.begin_rewire((a,b),'target')
                blank=board.mapFromScene(QPointF(100,-100))
                QTest.mouseMove(board.viewport(),blank,30)
                QTest.mouseClick(board.viewport(),Qt.MouseButton.LeftButton,pos=blank)
                self.assertIsNone(board.rewiring);self.assertIsNone(board.connection_preview)
                self.assertEqual(data['ports'][key]['target'],'bottom')
                self.assertTrue(all(edge.isVisible() for edge in board.edges))
                board.begin_rewire((c,b),'target');QTest.keyClick(board.viewport(),Qt.Key.Key_Escape)
                self.assertIsNone(board.rewiring)
                self.assertEqual({n:strip_references(v.read(n)[0]).encode() for n in v.notes()},original)
                saved=Boards(v).get(w.active_board);self.assertEqual(saved['ports'][key]['target'],'bottom')
            finally:w.close()
