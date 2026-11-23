import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from app import Window
from storage import Vault,ConflictError
from boards import Boards

class BoardFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_legacy_migration_independent_file_conflict_and_rename(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B');v.layout_path.parent.mkdir(exist_ok=True)
            original={'version':1,'tier_palette':3,'boards':[{'id':'civil','name':'Luật dân sự','positions':{a:[10,20],b:[300,20]},'edges':[[a,b]],'ports':{a+'\n'+b:{'source':'right','target':'left'}},'view':{'scale':0.8,'center':[200,80]}}],'active':'civil','open':['civil']}
            legacy=v.root/'.vision-law/boards.json';legacy.write_text(json.dumps(original,ensure_ascii=False))
            store=Boards(v);file=v.root/'Luật dân sự.vlaw'
            self.assertTrue(file.exists());self.assertEqual(json.loads(file.read_text())['board']['positions'][a],[10,20])
            self.assertTrue((v.root/'.vision-law/boards-before-independent-files.json').exists())
            self.assertEqual(json.loads(legacy.read_text()),original)
            duplicate=store.duplicate('civil','So sánh')
            self.assertNotEqual(duplicate,'civil')
            store.get(duplicate)['positions'][a]=[400,500];store.save()
            self.assertEqual(store.get('civil')['positions'][a],[10,20])
            store.rename('civil','Dân sự');self.assertFalse(file.exists());file=v.root/'Dân sự.vlaw';self.assertTrue(file.exists())
            store=Boards(v);self.assertEqual(store.get('civil')['name'],'Dân sự')
            payload=json.loads(file.read_text());payload['board']['positions'][a]=[999,888];file.write_text(json.dumps(payload))
            with self.assertRaises(ConflictError):store.save()
            reloaded=Boards(v);self.assertEqual(reloaded.get('civil')['positions'][a],[999,888])
            # Deleting a board does not delete its referenced Markdown files or reimport legacy.
            file.unlink();reloaded=Boards(v)
            self.assertNotIn('civil',[b['id'] for b in reloaded.data['boards']]);self.assertIn(duplicate,[b['id'] for b in reloaded.data['boards']]);self.assertTrue(v.path(a).exists())
    def test_tree_move_folder_note_and_camera(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);v.create_folder('Luật');a=v.create('A','Luật');b=v.create('B')
            w=Window(d);w.show();self.app.processEvents()
            try:
                with patch('app.QInputDialog.getText',return_value=('Dân sự',True)):
                    w.new_board()
                identity=w.active_board;self.assertIn(identity,w.board_tree_items)
                w.add_to_board([a,b]);w.add_connection(a,b)
                w.board.set_zoom(0.75);w.board.centerOn(250,125);w.save_layout()
                relative=w.boards.relative_path(identity)
                w.list.relocate(relative,'Luật/Dân sự.vlaw')
                self.assertEqual(w.boards.relative_path(identity),'Luật/Dân sự.vlaw')
                w.list.relocate('Luật','Pháp luật')
                self.assertEqual(w.boards.relative_path(identity),'Pháp luật/Dân sự.vlaw')
                self.assertIn('Pháp luật/A.md',w.boards.get(identity)['positions'])
                self.assertIn(('Pháp luật/A.md',b),w.connections)
                self.assertAlmostEqual(w.board.transform().m11(),0.75,places=5)
                w.open_board_id(identity);self.assertEqual(w.active_board,identity)
            finally:w.close()
