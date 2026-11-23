"""Run the GUI regression in a subprocess so a Qt layout hang is bounded."""
import os,subprocess,sys,unittest
from pathlib import Path

class OpenNoteFreezeTests(unittest.TestCase):
    def test_double_click_legacy_links_keeps_event_loop_responsive(self):
        script=r'''
import tempfile,time
from PyQt6.QtCore import QSettings,QTimer,Qt,QPointF
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from storage import Vault
from app import Window
from theme import apply_theme
app=QApplication([]);apply_theme(app)
with tempfile.TemporaryDirectory() as settings,tempfile.TemporaryDirectory() as d:
 QSettings.setDefaultFormat(QSettings.Format.IniFormat);QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,settings)
 v=Vault(d);a=v.create('Bảo đảm thực hiện nghĩa vụ');b=v.create('Tài sản bảo đảm')
 text,rev=v.read(a)
 v.save(a,text+'Nội dung ghi chú.\n\n## Khám phá\n\n[[Tài sản bảo đảm]]\n\n[[Tài sản bảo đảm|Một dẫn chiếu dài để kiểm tra khi văn bản xuống dòng]]\n\nĐọc tiếp ở đây.\n',rev)
 w=Window(d);w.show();app.processEvents();w.fit()
 baseline=v.read(a)[0]
 point=w.board.mapFromScene(w.board.cards[a].mapToScene(QPointF(100,55)))
 QTest.mouseDClick(w.board.viewport(),Qt.MouseButton.LeftButton,pos=point)
 assert a in w.documents
 heartbeats=[];timer=QTimer();timer.setInterval(30);timer.timeout.connect(lambda:heartbeats.append(time.monotonic()));timer.start()
 QTimer.singleShot(350,app.quit);start=time.monotonic();app.exec()
 assert time.monotonic()-start<3
 assert len(heartbeats)>=3
 assert v.read(a)[0]==baseline
 w.close()
print('responsive')
'''
        env=dict(os.environ,QT_QPA_PLATFORM='offscreen')
        result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).parent,env=env,capture_output=True,text=True,timeout=12)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertIn('responsive',result.stdout)
