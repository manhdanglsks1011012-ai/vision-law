"""Alt-Tab-style picker for internal document windows, invoked with Tab+Space."""
from pathlib import Path
from PyQt6.QtCore import QObject,QEvent,Qt,QSize
from PyQt6.QtGui import QKeyEvent,QIcon
from PyQt6.QtWidgets import QApplication,QWidget,QFrame,QVBoxLayout,QLabel,QListWidget,QListWidgetItem,QAbstractItemView,QPlainTextEdit,QLineEdit

class PageSwitcher(QObject):
    def __init__(self,window):
        super().__init__(window);self.window=window
        self.held=False;self.used=False;self.target=None;self.replaying=False;self.popup=None;self.choices=[]
        QApplication.instance().installEventFilter(self)
    def advance(self):
        desk=self.window.desk
        if self.popup is None:
            self.choices=[g for g in desk.mru if g is None or g in desk.groups]
            for group in [None]+desk.groups:
                if group not in self.choices:self.choices.append(group)
            self.popup=QFrame(self.window);self.popup.setObjectName('windowPicker')
            layout=QVBoxLayout(self.popup);layout.addWidget(QLabel('CHỌN CỬA SỔ · Space để chọn tiếp · thả Tab để mở · Esc hủy'))
            self.list=QListWidget();self.list.setViewMode(QListWidget.ViewMode.IconMode)
            self.list.setMovement(QListWidget.Movement.Static);self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
            self.list.setIconSize(QSize(200,120));self.list.setGridSize(QSize(220,165));self.list.setMinimumHeight(185)
            for group in self.choices:
                target=self.window.board if group is None else group
                title='Bảng chính' if group is None else group.sub.windowTitle()
                item=QListWidgetItem(QIcon(target.grab().scaled(200,120,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)),title)
                self.list.addItem(item)
            layout.addWidget(self.list);self.list.setCurrentRow(1 if len(self.choices)>1 else 0)
            self.popup.resize(min(self.window.width()-40,max(360,min(len(self.choices),4)*220+35)),240)
            self.popup.move((self.window.width()-self.popup.width())//2,(self.window.height()-self.popup.height())//2)
            self.popup.show();self.popup.raise_()
        else:self.list.setCurrentRow((self.list.currentRow()+1)%len(self.choices))
    def finish(self,commit=True):
        selected=self.choices[self.list.currentRow()] if self.popup else None
        had_popup=self.popup is not None
        if self.popup:self.popup.hide();self.popup.deleteLater();self.popup=None
        if commit and had_popup:self.window.desk.activate(selected)
    def eventFilter(self,obj,event):
        if self.replaying:return False
        if event.type()==QEvent.Type.ApplicationDeactivate:
            self.finish(False);self.held=False;self.target=None;return False
        if event.type() not in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):return False
        if not isinstance(obj,QWidget) or QWidget.window(obj) is not self.window:return False
        if self.popup and event.type()==QEvent.Type.KeyPress and event.key()==Qt.Key.Key_Escape:
            self.finish(False);self.used=True;return True
        if event.key()==Qt.Key.Key_Tab and event.modifiers()==Qt.KeyboardModifier.NoModifier:
            if event.isAutoRepeat():return True
            if event.type()==QEvent.Type.KeyPress:
                self.held=True;self.used=False;self.target=QApplication.focusWidget()
            else:
                if self.used:self.finish(True)
                elif self.held and isinstance(self.target,(QPlainTextEdit,QLineEdit)):
                    self.replaying=True
                    try:
                        QApplication.sendEvent(self.target,QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Tab,Qt.KeyboardModifier.NoModifier,'\t'))
                        QApplication.sendEvent(self.target,QKeyEvent(QEvent.Type.KeyRelease,Qt.Key.Key_Tab,Qt.KeyboardModifier.NoModifier,'\t'))
                    finally:self.replaying=False
                self.held=False;self.target=None
            return True
        if self.held and event.key()==Qt.Key.Key_Space:
            if event.type()==QEvent.Type.KeyPress:self.used=True;self.advance()
            return True
        if self.popup:return True
        return False
