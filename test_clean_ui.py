import tempfile,unittest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication,QLabel
from storage import Vault
from app import Window

class CleanWritingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_compact_body_title_preserves_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('Tiêu đề');b=v.create('Liên hệ');w=Window(d);w.resize(1500,950);w.show()
            try:
                w.add_connection(a,b);w.edit(a);self.app.processEvents();doc=w.documents[a]
                self.assertFalse(doc.input.toPlainText().startswith('# Tiêu đề'))
                self.assertTrue(doc.heading_label.isHidden())
                self.assertTrue(doc.source_toggle.isHidden())
                self.assertGreater(doc.center.width(),doc.panels['out'][0].width()*2)
                self.assertFalse(any(b in label.text() for card in doc.relationship_cards for label in card.findChildren(QLabel)))
                original=v.read(a)[0];self.assertTrue(doc.save());self.assertEqual(v.read(a)[0],original)
                doc.title_field.setText('Tiêu đề mới');doc.summary_field.setText('Một mô tả.');doc.input.setPlainText('Nội dung mới')
                self.assertTrue(doc.save())
                text=v.read(a)[0];self.assertIn('# Tiêu đề mới\n\nNội dung mới',text)
                doc.close();w.edit(a);self.app.processEvents();doc=w.documents[a]
                self.assertEqual(doc.title_field.text(),'Tiêu đề mới');self.assertEqual(doc.summary_field.text(),'Một mô tả.')
                self.assertEqual(doc.input.toPlainText(),'Nội dung mới')
            finally:w.close()
