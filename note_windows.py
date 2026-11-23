"""Internal document windows with movable tabs and content-only split panes."""
from pathlib import Path
from PyQt6.QtCore import Qt,QMimeData,QPoint,QEvent
from PyQt6.QtGui import QDrag,QColor,QCursor
from PyQt6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QTabWidget,QTabBar,
 QSplitter,QMdiArea,QMdiSubWindow,QMenu,QApplication,QInputDialog,QLabel,QSizeGrip)

class NoteTabBar(QTabBar):
    def __init__(self,tabs,manager):
        super().__init__(tabs);self.tabs=tabs;self.manager=manager;self.start=None;self.window_anchor=None
        self.setMovable(True);self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menu)
    def mousePressEvent(self,event):
        self.start=event.position().toPoint()
        self.window_anchor=event.globalPosition().toPoint()-self.tabs.group.sub.pos() if self.tabAt(self.start)<0 else None
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        pos=event.position().toPoint()
        if self.window_anchor is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.tabs.group.sub.move(event.globalPosition().toPoint()-self.window_anchor);return
        if self.start is not None and event.buttons() & Qt.MouseButton.LeftButton and (pos-self.start).manhattanLength()>QApplication.startDragDistance() and not self.rect().adjusted(-10,-15,10,15).contains(pos):
            index=self.tabAt(self.start)
            if index>=0:
                document=self.tabs.widget(index);mime=QMimeData();mime.setData('application/x-vision-note',document.name.encode())
                drag=QDrag(self);drag.setMimeData(mime);drag.setPixmap(document.grab().scaledToWidth(220))
                self.start=None
                result=drag.exec(Qt.DropAction.MoveAction)
                point=self.manager.area.mapFromGlobal(QCursor.pos())
                if result==Qt.DropAction.IgnoreAction and not (QApplication.mouseButtons() & Qt.MouseButton.LeftButton) and self.manager.area.rect().contains(point):
                    self.manager.detach(document)
                return
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event):self.start=None;self.window_anchor=None;super().mouseReleaseEvent(event)
    def dragEnterEvent(self,event):
        if event.mimeData().hasFormat('application/x-vision-note'):event.acceptProposedAction()
    def dragMoveEvent(self,event):event.acceptProposedAction()
    def dropEvent(self,event):
        name=bytes(event.mimeData().data('application/x-vision-note')).decode()
        if name in self.manager.window.documents:
            self.manager.move_document(self.manager.window.documents[name],self.tabs)
            event.acceptProposedAction()
    def menu(self,pos):
        index=self.tabAt(pos)
        if index<0:return
        document=self.tabs.widget(index);menu=QMenu(self)
        menu.addAction('Tách thành cửa sổ mới',lambda:self.manager.detach(document))
        menu.addAction('Chuyển sang nửa còn lại',lambda:self.tabs.group.move_to_other(document))
        menu.addAction('Đóng ghi chú',document.close)
        menu.exec(self.mapToGlobal(pos))

class WindowHandle(QLabel):
    def __init__(self,group):
        super().__init__('⠿');self.group=group;self.anchor=None
        self.setFixedSize(24,28);self.setToolTip('Kéo để di chuyển cửa sổ; nhấp đúp để phóng lớn')
        self.setCursor(Qt.CursorShape.SizeAllCursor)
    def mousePressEvent(self,event):self.anchor=event.globalPosition().toPoint()-self.group.sub.pos()
    def mouseMoveEvent(self,event):
        if self.anchor is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.group.sub.move(event.globalPosition().toPoint()-self.anchor)
    def mouseReleaseEvent(self,event):self.anchor=None
    def mouseDoubleClickEvent(self,event):
        sub=self.group.sub
        sub.showNormal() if sub.isMaximized() else sub.showMaximized()

class NoteGroup(QWidget):
    def __init__(self,manager):
        super().__init__();self.manager=manager;self.sub=None;self.split_mode=False;self.active_tabs=None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(0)
        self.splitter=QSplitter();root.addWidget(self.splitter,1)
        self.left=self.make_tabs();self.right=self.make_tabs();self.right.hide()
        self.splitter.addWidget(self.left);self.splitter.addWidget(self.right)
        corner=QWidget();tools=QHBoxLayout(corner);tools.setContentsMargins(0,0,3,0);tools.setSpacing(0)
        tools.addWidget(WindowHandle(self))
        new=QPushButton('＋');new.setToolTip('Mở ghi chú');new.setFixedSize(26,28);new.clicked.connect(self.open_note);tools.addWidget(new)
        self.split_button=QPushButton('◫');self.split_button.setFixedSize(26,28);self.split_button.setToolTip('Chia đôi nội dung')
        self.split_button.clicked.connect(self.toggle_split);tools.addWidget(self.split_button)
        menu=QPushButton('⋯');menu.setFixedSize(26,28);menu.setToolTip('Cửa sổ và về bảng');menu.clicked.connect(self.window_menu);tools.addWidget(menu)
        for button in corner.findChildren(QPushButton):button.setStyleSheet('padding:0; font-size:17px; border:none;')
        self.left.setCornerWidget(corner,Qt.Corner.TopRightCorner)
        footer=QWidget();footer.setFixedHeight(9)
        line=QHBoxLayout(footer);line.setContentsMargins(0,0,0,0);line.addStretch()
        self.size_grip=QSizeGrip(self);self.size_grip.setFixedSize(12,9);line.addWidget(self.size_grip)
        root.addWidget(footer)

    def window_menu(self):
        menu=QMenu(self)
        menu.addAction('Về bảng · Tab + Space',self.manager.window.show_board_page)
        menu.addAction('Chia đôi / Gộp nội dung',self.toggle_split)
        menu.addAction('Thu gọn cửa sổ',self.sub.showMinimized)
        menu.addAction('Phóng lớn / Khôi phục',lambda:self.sub.showNormal() if self.sub.isMaximized() else self.sub.showMaximized())
        menu.addAction('Đóng cửa sổ',self.sub.close)
        menu.exec(self.cursor().pos())

    def make_tabs(self):
        tabs=QTabWidget();tabs.setObjectName('noteTabs');tabs.group=self;tabs.setTabBar(NoteTabBar(tabs,self.manager))
        tabs.setTabsClosable(True);tabs.setDocumentMode(True)
        tabs.tabCloseRequested.connect(lambda index:tabs.widget(index).close())
        tabs.currentChanged.connect(lambda _:self.changed(tabs))
        return tabs
    def changed(self,tabs):
        document=tabs.currentWidget()
        if document:
            self.active_tabs=tabs
            self.manager.window.current_document=document.name
            document.setFocus(Qt.FocusReason.OtherFocusReason)
            self.update_title()
    def update_title(self):
        names=[Path(d.name).stem for d in self.documents()]
        if self.sub:self.sub.setWindowTitle(' / '.join(names) or 'Ghi chú')
        for tabs in (self.left,self.right):
            for index in range(tabs.count()):
                document=tabs.widget(index)
                button=QPushButton('×');button.setFixedSize(18,18);button.setToolTip('Đóng ghi chú')
                button.setStyleSheet('QPushButton { padding:0; border:none; color:#9e98aa; font-size:17px; } QPushButton:hover { color:#fff; background:#4a4156; }')
                button.clicked.connect(lambda checked=False,d=document:d.close())
                tabs.tabBar().setTabButton(index,QTabBar.ButtonPosition.RightSide,button)
    def documents(self):return [tabs.widget(i) for tabs in (self.left,self.right) for i in range(tabs.count())]
    def open_note(self):
        names=self.manager.window.names
        name,ok=QInputDialog.getItem(self,'Mở ghi chú','Ghi chú:',names,0,False)
        if ok:self.manager.window.edit(name)
    def toggle_split(self):
        if self.split_mode:
            for i in range(self.right.count()-1,-1,-1):self.manager.move_document(self.right.widget(i),self.left,cleanup=False)
            self.split_mode=False;self.right.hide()
        else:
            if self.left.count()<2:
                self.open_note()
            if self.left.count()<2:return
            self.split_mode=True;self.right.show()
            self.manager.move_document(self.left.widget(self.left.count()-1),self.right,cleanup=False)
        self.refresh_mode()
    def refresh_mode(self):
        if not self.right.count():self.split_mode=False;self.right.hide()
        self.split_button.setToolTip('Thoát chia đôi' if self.split_mode else 'Chia đôi nội dung')
        for d in self.documents():d.set_content_only(self.split_mode)
        self.splitter.setSizes([self.width()//2,self.width()//2])
    def move_to_other(self,document):
        target=self.right if self.left.indexOf(document)>=0 else self.left
        self.split_mode=True;self.right.show();self.manager.move_document(document,target,cleanup=False);self.refresh_mode()

class NoteSubWindow(QMdiSubWindow):
    def __init__(self,manager):
        super().__init__();self.manager=manager
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setObjectName('noteSubWindow')
    def moveEvent(self,event):
        super().moveEvent(event)
        if self.isMaximized() or self.isMinimized():return
        area=self.manager.area
        x=max(0,min(self.x(),max(0,area.width()-self.width())))
        y=max(0,min(self.y(),max(0,area.height()-self.height())))
        if x!=self.x() or y!=self.y():self.move(x,y)
    def closeEvent(self,event):
        for document in list(self.widget().documents()):
            if not document.close():event.ignore();return
        event.accept()

class DocumentDesk:
    def __init__(self,window):
        self.window=window;self.groups=[];self.mru=[None];self.current=None
        self.area=QMdiArea(window);self.area.setBackground(QColor('#19181e'))
        self.area.setStyleSheet('QMdiArea { border: 1px solid #39333f; }')
        self.area.subWindowActivated.connect(self.activated)
        self.area.hide()
    def resize(self):
        self.area.setGeometry(self.window.centralWidget().geometry())
        # Clamp floating windows when the desk shrinks.
        for group in self.groups:
            sub=group.sub
            if sub.isMaximized():continue
            sub.resize(min(sub.width(),self.area.width()),min(sub.height(),self.area.height()))
            sub.move(max(0,min(sub.x(),self.area.width()-sub.width())),max(0,min(sub.y(),self.area.height()-sub.height())))
    def activated(self,sub):
        if not sub:return
        group=sub.widget();self.current=group
        self.touch(group)
        document=(group.active_tabs.currentWidget() if group.active_tabs else None) or group.left.currentWidget() or group.right.currentWidget()
        if document:self.window.current_document=document.name
        group.setFocus(Qt.FocusReason.OtherFocusReason)
    def touch(self,group):
        if group in self.mru:self.mru.remove(group)
        self.mru.insert(0,group)
    def new_group(self):
        group=NoteGroup(self);sub=NoteSubWindow(self);group.sub=sub;sub.setWidget(group)
        self.area.addSubWindow(sub);self.groups.append(group)
        margin=50;sub.resize(max(620,self.area.width()-margin*2),max(440,self.area.height()-margin*2))
        offset=(len(self.groups)-1)%4*18;sub.move(35+offset,35+offset)
        sub.show();return group
    def locate(self,document):
        for group in self.groups:
            for tabs in (group.left,group.right):
                if tabs.indexOf(document)>=0:return group,tabs
        return None,None
    def open(self,document,new_window=False):
        self.resize();self.area.show();self.area.raise_()
        group,tabs=self.locate(document)
        if group is None:
            group=self.new_group() if new_window or self.current not in self.groups else self.current
            tabs=group.left;tabs.addTab(document,Path(document.name).stem)
        group.active_tabs=tabs
        tabs.setCurrentWidget(document);document.show();document.set_content_only(group.split_mode)
        self.area.setActiveSubWindow(group.sub);group.sub.showNormal() if group.sub.isMinimized() else None
        group.sub.raise_();self.current=group;self.touch(group)
        self.window.current_document=document.name;document.setFocus(Qt.FocusReason.OtherFocusReason);group.update_title()
    def board(self):
        self.area.hide();self.current=None;self.window.current_document=None
        self.touch(None);self.window.board.setFocus()
    def detach(self,document):
        group=self.new_group();self.move_document(document,group.left);self.open(document)
    def move_document(self,document,target,cleanup=True):
        group,source=self.locate(document)
        if source is target:return
        if source:source.removeTab(source.indexOf(document))
        target.addTab(document,Path(document.name).stem);target.setCurrentWidget(document)
        document.show();document.set_content_only(target.group.split_mode)
        document.setFocus(Qt.FocusReason.OtherFocusReason)
        if group:
            if cleanup:self.cleanup(group)
            else:group.update_title()
        target.group.update_title()
    def cleanup(self,group):
        if not group.documents():
            self.groups.remove(group)
            if group in self.mru:self.mru.remove(group)
            group.sub.hide();self.area.removeSubWindow(group.sub);group.sub.deleteLater()
            if self.current is group:self.current=None
        else:group.refresh_mode();group.update_title()
    def document_closed(self,name):
        document=self.window.documents.pop(name,None)
        if name in self.window.document_order:self.window.document_order.remove(name)
        if document:
            group,tabs=self.locate(document)
            if tabs:tabs.removeTab(tabs.indexOf(document));self.cleanup(group)
        if not self.groups:self.board()
        else:
            group=self.current if self.current in self.groups else self.groups[-1]
            candidate=(group.active_tabs.currentWidget() if group.active_tabs else None) or group.left.currentWidget() or group.right.currentWidget()
            if candidate:self.open(candidate)
    def activate(self,group):
        if group is None:self.board();return
        if group in self.groups:
            document=(group.active_tabs.currentWidget() if group.active_tabs else None) or group.left.currentWidget() or group.right.currentWidget()
            if document:self.open(document)
