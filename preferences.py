from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (QDialog, QFormLayout, QComboBox, QSpinBox, QCheckBox,
    QDialogButtonBox, QKeySequenceEdit, QLabel, QMessageBox)

DEFAULT_KEYS={'new':'Ctrl+N', 'folder':'Ctrl+Shift+N', 'search':'Ctrl+Shift+F', 'vault':'Ctrl+O', 'settings':'Ctrl+,'}
class Preferences:
    def __init__(self):
        self.store=QSettings('VisionLaw', 'VisionLaw')
    def get(self, key, default):
        return self.store.value(key, default, type=type(default))
    def set(self,key,value): self.store.setValue(key,value)

class SettingsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.setWindowTitle('Cài đặt — Vision law'); self.resize(560,480)
        self.window=window
        form=QFormLayout(self)
        form.setSpacing(15)
        form.addRow(QLabel('SOẠN THẢO & LƯU TRỮ'))
        self.location=QComboBox()
        self.location.addItem('Thư mục gốc vault','')
        self.location.addItem('Thư mục đang chọn','@selected')
        if window.vault:
            for f in window.vault.folders(): self.location.addItem(f,f)
        index=self.location.findData(window.vault_pref('new_folder',''))
        self.location.setCurrentIndex(max(0,index))
        form.addRow('Ghi chú mới đặt tại',self.location)
        self.size=QSpinBox(); self.size.setRange(12,24); self.size.setValue(window.prefs.get('editor_size',15))
        form.addRow('Cỡ chữ soạn thảo',self.size)
        self.autosave=QCheckBox('Tự lưu sau 2 giây ngừng nhập')
        self.autosave.setChecked(window.prefs.get('autosave',False)); form.addRow(self.autosave)
        self.grid=QCheckBox('Hiện lưới chấm trên bảng'); self.grid.setChecked(window.prefs.get('grid',True)); form.addRow(self.grid)
        self.triple_click=QCheckBox('Bấm nhanh 3 lần lên đường ống để bỏ liên kết')
        self.triple_click.setChecked(window.prefs.get('triple_click_unlink',True))
        form.addRow(self.triple_click)
        form.addRow(QLabel('PHÍM TẮT'))
        self.keys={}
        for key,label in [('new','Tạo ghi chú'),('folder','Tạo thư mục'),('search','Tìm kiếm'),('vault','Đổi vault'),('settings','Cài đặt')]:
            field=QKeySequenceEdit(QKeySequence(window.prefs.get('key_'+key,DEFAULT_KEYS[key])))
            self.keys[key]=field; form.addRow(label,field)
        form.addRow(QLabel('Lưu thủ công: Ctrl+S • Cấu hình vị trí ghi chú được nhớ riêng từng vault.'))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('Lưu cài đặt')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Hủy')
        buttons.accepted.connect(self.commit); buttons.rejected.connect(self.reject); form.addRow(buttons)
    def commit(self):
        keys={k:f.keySequence().toString() for k,f in self.keys.items()}
        if any(not v for v in keys.values()) or len(set(keys.values()))!=len(keys) or any(key in keys.values() for key in ('Ctrl+S','Ctrl+Z','Ctrl+Y')):
            QMessageBox.warning(self,'Phím tắt','Phím tắt phải khác nhau, không trống và không dùng Ctrl+S, Ctrl+Z hoặc Ctrl+Y.'); return
        w=self.window
        w.set_vault_pref('new_folder',self.location.currentData())
        for key,value in [('editor_size',self.size.value()),('autosave',self.autosave.isChecked()),('grid',self.grid.isChecked()),('triple_click_unlink',self.triple_click.isChecked())]: w.prefs.set(key,value)
        for key,value in keys.items(): w.prefs.set('key_'+key,value)
        w.board.cancel_edge_click()
        w.apply_shortcuts(); w.board.viewport().update(); self.accept()
