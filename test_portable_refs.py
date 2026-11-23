import tempfile,unittest,json
from unittest.mock import patch
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication,QMessageBox
from app import Window,Editor
from storage import Vault,ConflictError
from boards import Boards
from portable_refs import strip_references,read_manifest,START,END

class PortableReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_export_hidden_editor_merge_history_and_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B');c=v.create('C');w=Window(d);w.show()
            try:
                w.edit(a);doc=w.documents[a];doc.input.insertPlainText('Bản nháp')
                w.add_connection(a,b)
                data=w.boards.get(w.active_board)
                data.setdefault('edge_categories',{})[a+'\n'+b]=['explanation']
                data.setdefault('edge_styles',{})[a+'\n'+b]={'label':'Giải thích điều kiện'};w.boards.save()
                text=v.read(a)[0];self.assertIn('[[B]]',text);self.assertIn('Giải thích',text);self.assertIn('Giải thích điều kiện',text)
                self.assertNotIn(START,doc.input.toPlainText());self.assertNotIn('Dẫn chiếu',doc.preview.toPlainText())
                self.assertTrue(doc.save());self.assertIn('Bản nháp',v.read(a)[0]);self.assertIn('[[B]]',v.read(a)[0])
                exported=v.read(a)[0];w.boards.save();self.assertEqual(v.read(a)[0],exported)
                w.remove_connection((a,b));self.assertIn('[[B]]',v.read(a)[0])
                self.assertTrue((v.root/'.vision-law/reference-backups'/a).exists())
                # An actual external content edit is still rejected, keeping the draft.
                doc.input.insertPlainText('another draft')
                current,rev=v.read(a);v.save(a,current.replace('Bản nháp','Sửa ngoài app'),rev)
                with patch('app.QMessageBox.warning') as warning:
                    self.assertFalse(doc.save());warning.assert_called_once()
                self.assertIn('another draft',doc.input.toPlainText())
            finally:
                with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):w.close()
    def test_migrate_existing_boards_deduplicate_and_rename(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B')
            text,rev=v.read(a);v.save(a,text+'[[B]]\n',rev)
            v.layout_path.parent.mkdir(exist_ok=True)
            path=v.root/'.vision-law/boards.json'
            board={'id':'one','name':'Luật','positions':{a:[0,0],b:[300,0]},'edges':[[a,b]],'edge_categories':{a+'\n'+b:['explanation']},'relation_categories':[{'id':'explanation','name':'Giải thích','color':'#abcabc'}]}
            path.write_text(json.dumps({'version':1,'boards':[board,{**board,'id':'two','name':'So sánh'}],'active':'one','open':['one'],'tier_palette':3}))
            store=Boards(v);text=v.read(a)[0]
            self.assertEqual(text.count('[[B]]'),1)
            self.assertEqual(len(read_manifest(text)[b]),2)
            v.relocate(b,'New.md');Boards(v)
            text=v.read(a)[0];self.assertNotIn('[[B]]',text);self.assertIn('[[New]]',text)
            self.assertNotIn(b,read_manifest(text));self.assertIn('New.md',read_manifest(text))
