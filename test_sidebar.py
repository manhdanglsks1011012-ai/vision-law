import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from app import Window, Editor
from preferences import SettingsDialog
from storage import Vault

class SidebarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings_tmp=tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.settings_tmp.name)
        cls.app=QApplication.instance() or QApplication([])

    def test_folder_creation_paths(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d)
            v.create_folder('Luật'); v.create_folder('Dân sự','Luật')
            name=v.create('Nghĩa vụ','Luật/Dân sự')
            self.assertEqual(name,'Luật/Dân sự/Nghĩa vụ.md')
            self.assertIn('Luật/Dân sự',v.folders())
            for name in ('../bad','.hidden','a/b'):
                with self.assertRaises(ValueError): v.create_folder(name)
            with self.assertRaises(ValueError): v.create('X','../')
            with self.assertRaises(FileExistsError): v.create_folder('Luật')

    def test_settings_tree_switch_and_autosave(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            v=Vault(a); v.create_folder('Luật'); v.create_folder('Rỗng'); v.create_folder('Dân sự','Luật')
            name=v.create('A','Luật/Dân sự')
            w=Window(a)
            try:
                w.show(); self.app.processEvents()
                self.assertEqual(w.list.topLevelItemCount(),3)
                w.list.setCurrentItem(w.tree_items[name])
                self.assertEqual(w.selected_folder(),'Luật/Dân sự')
                with patch('app.QInputDialog.getText',return_value=('Thương mại',True)):
                    w.create_folder()
                self.assertTrue((Path(a)/'Luật/Dân sự/Thương mại').is_dir())
                dialog=SettingsDialog(w)
                dialog.location.setCurrentIndex(dialog.location.findData('Luật/Dân sự'))
                dialog.autosave.setChecked(True); dialog.size.setValue(18); dialog.commit()
                self.assertEqual(w.vault_pref('new_folder',''),'Luật/Dân sự')
                with patch('app.QInputDialog.getText',return_value=('B',True)), patch.object(w,'edit'):
                    w.create()
                self.assertTrue((Path(a)/'Luật/Dân sự/B.md').exists())
                e=Editor(w,name); e.input.setPlainText('Tự lưu [[B]]')
                QTest.qWait(2200)
                self.assertEqual(v.read(name)[0],'Tự lưu [[B]]')
                self.assertFalse(e.input.document().isModified()); e.close()
                w.board.cards[name].setPos(90,130)
                w.load(b)
                self.assertEqual(w.names,[])
                self.assertEqual(w.vault_pref('new_folder',''),'')
                w.load(a)
                self.assertEqual(w.vault_pref('new_folder',''),'Luật/Dân sự')
                self.assertEqual(w.board.cards[name].x(),90)
                self.assertIn(a,w.prefs.get('recent_vaults',[]))
                self.assertEqual(len(w.shortcuts),5)
            finally:
                w.close()
