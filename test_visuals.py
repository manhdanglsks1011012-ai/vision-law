import tempfile
import unittest
from unittest.mock import patch
from PyQt6.QtCore import Qt,QPointF,QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from app import Window,Editor,Card
from storage import Vault
from card_visuals import COLORS,details

class VisualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])

    def test_details_styles_pipes_and_vertical_ports_persist(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B');w=Window(d)
            try:
                editor=Editor(w,a)
                editor.title_field.setText('Tiêu đề do tôi viết')
                editor.summary_field.setText('Một câu mô tả ngắn.')
                self.assertTrue(editor.save());editor.close()
                self.assertEqual(details(v.read(a)[0],a),('Tiêu đề do tôi viết','Một câu mô tả ngắn.'))
                self.assertNotIn('vision-law-card',editor.preview.toPlainText())
                first=w.active_board
                w.show();self.app.processEvents();w.fit()
                w.board.cards[a].setSelected(True);self.app.processEvents()
                self.assertIsNotNone(w.board.palette)
                w.board.set_style(a,tier=4)
                self.assertEqual(w.boards.get(first)['styles'][a]['color'],COLORS[3])
                w.board.set_style(a,color=COLORS[6])
                w.board.cards[b].setPos(0,260);w.fit();self.app.processEvents()
                start=w.board.mapFromScene(w.board.cards[a].mapToScene(Card.PORTS['bottom']))
                end=w.board.mapFromScene(w.board.cards[b].mapToScene(Card.PORTS['top']))
                QTest.mousePress(w.board.viewport(),Qt.MouseButton.LeftButton,pos=start)
                QTest.mouseMove(w.board.viewport(),end,30)
                QTest.mouseRelease(w.board.viewport(),Qt.MouseButton.LeftButton,pos=end)
                self.assertEqual(w.connections,[(a,b)])
                port=w.boards.get(first)['ports'][a+'\n'+b]
                self.assertEqual(port,{'source':'bottom','target':'top'})
                pipe=w.board.edges[0]
                self.assertEqual(pipe.color.name(),COLORS[6])
                self.assertEqual(pipe.path().pointAtPercent(0),w.board.cards[a].mapToScene(Card.PORTS['bottom']))
                phase=w.board.flow_phase;w.board.animate_pipes();self.assertGreater(w.board.flow_phase,phase)
                w.board.cards[a].setPos(40,20);self.app.processEvents()
                self.assertEqual(w.board.palette.pos(),w.board.cards[a].pos()+QPointF(-30,126))
                w.list.relocate(a,'New.md')
                data=w.boards.get(first)
                self.assertEqual(data['styles']['New.md']['tier'],4)
                self.assertIn('New.md\n'+b,data['ports'])
                with patch('app.QInputDialog.getText',return_value=('Second',True)):w.new_board()
                w.add_to_board(['New.md',b]);w.board.set_style('New.md',tier=10)
                w.tabs.setCurrentIndex(0)
                self.assertEqual(w.boards.get(first)['styles']['New.md']['tier'],4)
            finally:w.close()
            reopened=Window(d)
            try:
                self.assertEqual(reopened.boards.get(first)['styles']['New.md']['color'],COLORS[6])
                self.assertEqual(reopened.board.cards['New.md'].summary,'Một câu mô tả ngắn.')
            finally:reopened.close()
