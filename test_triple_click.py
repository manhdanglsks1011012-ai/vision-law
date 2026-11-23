from portable_refs import strip_references
import json,tempfile,unittest
from PyQt6.QtCore import Qt,QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from app import Window
from storage import Vault
from boards import Boards
from card_visuals import COLORS,OLD_TIER_COLORS
from preferences import SettingsDialog

class TripleClickTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_gesture_setting_and_unchanged_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B');w=Window(d);w.show()
            originals={n:v.path(n).read_bytes() for n in v.notes()}
            try:
                w.prefs.set('triple_click_unlink',True);w.add_connection(a,b);w.fit();self.app.processEvents()
                board=w.board;point=board.mapFromScene(board.edges[0].path().pointAtPercent(0.5))
                QTest.mouseClick(board.viewport(),Qt.MouseButton.LeftButton,pos=point)
                QTest.mouseDClick(board.viewport(),Qt.MouseButton.LeftButton,pos=point)
                QTest.mouseClick(board.viewport(),Qt.MouseButton.LeftButton,pos=point)
                self.assertEqual(w.connections,[])
                QTest.qWait(QApplication.doubleClickInterval()+20)
                self.assertIsNone(board.edge_editor)
                self.assertEqual({n:strip_references(v.read(n)[0]).encode() for n in v.notes()},originals)
                self.assertEqual(Boards(v).get(w.active_board)['edges'],[])
                settings=SettingsDialog(w);settings.triple_click.setChecked(False);settings.commit()
                self.assertFalse(w.prefs.get('triple_click_unlink',True))
                w.add_connection(a,b)
                self.app.processEvents()
                point=board.mapFromScene(board.edges[0].path().pointAtPercent(0.5))
                for _ in range(3):QTest.mouseClick(board.viewport(),Qt.MouseButton.LeftButton,pos=point)
                self.assertEqual(w.connections,[(a,b)])
                for _ in range(100):
                    if board.edge_editor is not None:break
                    QTest.qWait(20)
                self.assertIsNotNone(board.edge_editor);board.edge_editor.close()
            finally:w.close()
    def test_tier_palette_migration_preserves_custom_color(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B');store=Boards(v)
            store.data.pop('tier_palette',None)
            store.get(store.data['active'])['styles']={a:{'tier':1,'color':OLD_TIER_COLORS[0]},b:{'tier':10,'color':'#123456','custom_color':True}}
            store.save();migrated=Boards(v);styles=migrated.get(migrated.data['active'])['styles']
            self.assertEqual(styles[a]['color'],COLORS[0]);self.assertEqual(COLORS[0],'#f06464')
            self.assertEqual(styles[b]['color'],'#123456');self.assertEqual(COLORS[9],'#9ba0a8')
