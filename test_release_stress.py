import json,tempfile,time,unittest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings,QTimer
from app import Window
from storage import Vault

class ReleaseLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_300_notes_299_links_open_edit_and_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            names=['Note '+str(i)+'.md' for i in range(300)]
            for name in names:(root/name).write_text('# '+Path(name).stem+'\n\nNội dung kiểm tra.\n')
            board={'id':'load','name':'Load','positions':{n:[(i%20)*310,(i//20)*180] for i,n in enumerate(names)},'edges':[[names[i],names[i+1]] for i in range(299)]}
            (root/'Load.vlaw').write_text(json.dumps({'format':'vision-law-board','version':1,'board':board}))
            start=time.monotonic();w=Window(d);w.show();self.app.processEvents();w.fit()
            try:
                self.assertEqual(len(w.board.cards),300);self.assertEqual(len(w.connections),299)
                w.edit(names[150]);self.app.processEvents()
                self.assertIn(names[150],w.documents)
                self.assertLess(time.monotonic()-start,20)
                doc=w.documents[names[150]];doc.input.insertPlainText('Bổ sung');self.assertTrue(doc.save())
            finally:w.close()
            reopened=Window(d)
            try:self.assertEqual(len(reopened.board.cards),300);self.assertEqual(len(reopened.connections),299)
            finally:reopened.close()
