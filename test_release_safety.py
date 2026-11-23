import json,tempfile,unittest,os,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication,QMessageBox
from PyQt6.QtCore import QSettings,QCoreApplication
from app import Window
from boards import Boards
from storage import Vault,atomic_write
from vault_lock import VaultLease

class ReleaseSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,cls.tmp.name)
        cls.app=QApplication.instance() or QApplication([])
    def test_no_vault_view_is_safe(self):
        w=Window()
        try:w.restore_board_view();w.board.history.activate()
        finally:w.close()
    def test_single_writer_lease_releases(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);lease=VaultLease(root)
            with self.assertRaises(RuntimeError):VaultLease(root)
            lease.release();second=VaultLease(root);second.release()
    def test_atomic_replace_failure_and_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'A.md';path.write_text('old');path.chmod(0o640)
            with patch('storage.os.replace',side_effect=OSError('injected disk failure')):
                with self.assertRaises(OSError):atomic_write(path,'new')
            self.assertEqual(path.read_text(),'old');self.assertEqual(len(list(Path(d).iterdir())),1)
            atomic_write(path,'new');self.assertEqual(path.stat().st_mode & 0o777,0o640)
    def test_invalid_board_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            v=Vault(d);a=v.create('A');store=Boards(v);identity=store.data['active'];file=v.root/store.relative_path(identity)
            original=file.read_bytes();board=store.get(identity)
            for invalid in ({'../escape.md':[0,0]},{a:[float('nan'),2]},{a:['bad',0]}):
                board['positions']=invalid
                with self.assertRaises(ValueError):store.save()
                self.assertEqual(file.read_bytes(),original)
    def test_recovery_restores_draft_without_overwrite(self):
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as state:
            v=Vault(d);a=v.create('A');w=Window(d);w.show();w.edit(a);doc=w.documents[a]
            original=v.read(a)[0];doc.input.setPlainText('Bản nháp cần khôi phục')
            try:
                from runtime import save_recovery,offer_recovery
                with patch('runtime.data_dir',return_value=Path(state)):
                    save_recovery(w)
                    with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):w.close_documents()
                    with patch('PyQt6.QtWidgets.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):offer_recovery(w)
                    self.assertEqual(w.documents[a].input.toPlainText(),'Bản nháp cần khôi phục')
                    self.assertEqual(v.read(a)[0],original)
                    self.assertTrue(list(Path(state).rglob('*.archive.json')))
            finally:
                with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):w.close()
    def test_committed_note_survives_process_kill(self):
        with tempfile.TemporaryDirectory() as d:
            script="from storage import Vault; import os,sys; v=Vault(sys.argv[1]); n=v.create('Atomic'); text,rev=v.read(n); v.save(n,'Đã lưu trước khi dừng đột ngột',rev); os._exit(0)"
            result=subprocess.run([sys.executable,'-c',script,d],cwd=Path(__file__).parent,timeout=5)
            self.assertEqual(result.returncode,0);self.assertEqual((Path(d)/'Atomic.md').read_text(),'Đã lưu trước khi dừng đột ngột')
