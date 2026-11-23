from portable_refs import strip_references
import tempfile
import unittest
from unittest.mock import patch
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication,QPushButton,QMessageBox
from app import Window
from storage import Vault
from dossier import LinkEntry,related

class DossierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])

    def test_groups_many_records_scopes_and_stack_preserve_drafts(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);v.create_folder('Luật');v.create_folder('Khác')
            a=v.create('A','Luật');others=[v.create('B'+str(i),'Luật') for i in range(5)];foreign=v.create('X','Khác')
            w=Window(d);w.show()
            try:
                for other in others:w.add_connection(a,other)
                w.add_connection(foreign,a)
                w.edit(a);self.app.processEvents();doc=w.documents[a]
                self.assertEqual(len(related(w,a,'out')),5)
                self.assertEqual(len(related(w,a,'in')),1)
                self.assertEqual(len(doc.relationship_cards),4)  # first 3 outbound + 1 inbound
                more=next(b for b in doc.findChildren(QPushButton) if b.text()=='Xem thêm 2 tài liệu')
                more.click();self.app.processEvents()
                self.assertEqual(len(doc.relationship_cards),6)
                with patch('dossier.QInputDialog.getText',return_value=('Điều kiện',True)):doc.add_group('out')
                group=next(c for c in doc.config('out') if c['name']=='Điều kiện')
                doc.add_relation('out',group['id'],others[0])
                self.assertIn(group['id'],w.boards.get(w.active_board)['edge_categories'][a+'\n'+others[0]])
                self.assertEqual(len(w.connections),6)
                entry=LinkEntry(doc,'out',None);entry.show()
                entry.input.setText('[[');self.app.processEvents()
                entry.scope.setCurrentIndex(1)
                self.assertNotIn(foreign,entry.candidates)
                self.assertIn(others[1],entry.candidates)
                entry.scope.setCurrentIndex(0);self.assertIn(foreign,entry.candidates)
                entry.input.setText('[[B1');self.assertEqual(entry.candidates,[others[1]])
                # Forward/input relation and a custom group are the same board relation.
                doc.add_relation('in',None,others[2]);self.assertIn((others[2],a),w.connections)
                doc.input.setPlainText('Bản nháp chưa lưu')
                doc.input.setPlainText('Bản nháp [[Không cho phép]]')
                self.assertEqual(doc.input.toPlainText(),'Bản nháp chưa lưu')
                w.edit(others[0]);self.app.processEvents()
                self.assertEqual(len(w.documents),2)
                w.edit(a);self.assertEqual(len(w.documents),2)
                self.assertIs(w.documents[a],doc)
                self.assertEqual(doc.input.toPlainText(),'Bản nháp chưa lưu')
                with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel):
                    self.assertFalse(w.close_documents())
                self.assertIn(a,w.documents)
                self.assertTrue(doc.save())
                w.close_documents()
                w.reload()
                self.assertIn(group['id'],w.boards.get(w.active_board)['edge_categories'][a+'\n'+others[0]])
                entry.close()
            finally:
                with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):w.close()

    def test_create_from_suggestion_and_all_board_scope(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B');w=Window(d);w.show()
            try:
                w.add_connection(a,b)
                with patch('app.QInputDialog.getText',return_value=('Second',True)):w.new_board()
                w.add_to_board([a,b]);w.add_connection(b,a)
                w.edit(a);self.app.processEvents();doc=w.documents[a]
                self.assertEqual(len(related(w,a,'out')),0)
                self.assertEqual(len(related(w,a,'out',True)),1)
                doc.scope.setCurrentIndex(1);self.app.processEvents()
                self.assertEqual(len(doc.relationship_cards),2)
                doc.scope.setCurrentIndex(0);self.app.processEvents()
                panel=doc.panels['out'][1]
                next(b for b in panel.findChildren(QPushButton) if b.isVisible() and b.toolTip()=='Thêm dẫn chiếu vào Chưa phân loại').click()
                entry=next(e for e in doc.findChildren(LinkEntry) if e.side=='out' and e.isVisible())
                entry.input.setText('[[New');self.app.processEvents()
                entry.results.setCurrentRow(len(entry.candidates))
                with patch('dossier.QInputDialog.getText',return_value=('New',True)),patch('dossier.QInputDialog.getItem',return_value=('Gốc vault',True)):
                    entry.choose()
                self.assertTrue(v.path('New.md').exists())
                self.assertIn((a,'New.md'),w.connections)
                self.assertIs(w.documents[a],doc)
            finally:w.close()

    def test_select_suggestion_adds_relation_not_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');b=v.create('B')
            originals={n:v.path(n).read_bytes() for n in v.notes()}
            w=Window(d);w.show()
            try:
                w.edit(a);self.app.processEvents();doc=w.documents[a]
                panel=doc.panels['out'][1]
                next(b for b in panel.findChildren(QPushButton) if b.isVisible() and b.toolTip()=='Thêm dẫn chiếu vào Chưa phân loại').click()
                entry=next(e for e in doc.findChildren(LinkEntry) if e.side=='out' and e.isVisible())
                entry.input.setText('[[B');self.app.processEvents()
                self.assertEqual(entry.candidates,[b]);entry.results.setCurrentRow(0);entry.choose()
                self.assertIn((a,b),w.connections)
                self.assertEqual({n:strip_references(v.read(n)[0]).encode() for n in v.notes()},originals)
                w.edit(b);self.app.processEvents()
                self.assertEqual(len(related(w,b,'in')),1)
            finally:w.close()
