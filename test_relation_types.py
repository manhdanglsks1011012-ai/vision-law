import tempfile,unittest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication,QLabel
from app import Window
from storage import Vault
from boards import Boards
from relation_types import ensure_categories,merged_relations

class SemanticRelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_merge_category_shared_directions_minimal_titles_and_rename(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B');c=v.create('C')
            text,rev=v.read(a);v.save(a,text+'\n[[B]]\n[[C]]',rev)
            w=Window(d);w.show()
            try:
                w.add_connection(a,b);w.edit(a);self.app.processEvents();doc=w.documents[a]
                records=merged_relations(w,a,'out');self.assertEqual(len(records),2)
                self.assertEqual(len({r['pair'] for r in records}),2)
                doc.set_categories((a,b),['explanation','example'])
                doc.set_categories((a,c),['exception'])
                self.assertEqual(w.board.edges[0].label,'Giải thích · Ví dụ minh họa')
                self.assertEqual(set(merged_relations(w,b,'in')[0]['categories']),{'explanation','example'})
                legacy=next(r for r in merged_relations(w,a,'out') if r['other']==c)
                self.assertTrue(legacy['legacy']);self.assertEqual(legacy['categories'],['exception'])
                self.assertEqual(len(doc.relationship_cards),3)  # B in two meaningful groups, C in one
                labels=[label.text() for row in doc.relationship_cards for label in row.findChildren(QLabel)]
                self.assertFalse(any('.md' in label for label in labels))
                self.assertFalse(any('Dẫn chiếu trong tệp' in label for label in labels))
                original=v.read(a)[0];w.close_documents();w.list.relocate(b,'New B.md')
                data=w.boards.get(w.active_board);self.assertIn(a+'\nNew B.md',data['edge_categories'])
                self.assertIn('[[New B]]',v.read(a)[0])
                saved=Boards(v).get(w.active_board)
                self.assertEqual(saved['edge_categories'][a+'\n'+c],['exception'])
            finally:w.close()
    def test_old_group_migration_preserves_members(self):
        board={'dossiers':{'A.md':{'out':[{'id':'old','name':'Căn cứ','color':'#123456','members':['B.md']}]}},'edges':[]}
        ensure_categories(board)
        self.assertEqual(board['edge_categories']['A.md\nB.md'],['old'])
        self.assertIn('Căn cứ',[c['name'] for c in board['relation_categories']])
        ensure_categories(board);self.assertEqual(len(board['relation_categories']),5)
