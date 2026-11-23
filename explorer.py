from pathlib import Path
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QMessageBox
from icons import icon

NOTE = Qt.ItemDataRole.UserRole
FOLDER = NOTE + 1
BOARD = NOTE + 2

class ExplorerItem(QTreeWidgetItem):
    def __lt__(self, other):
        a, b = self.data(0,FOLDER) is not None, other.data(0,FOLDER) is not None
        return a if a != b else self.text(0).casefold() < other.text(0).casefold()

class Explorer(QTreeWidget):
    def __init__(self, window):
        super().__init__()
        self.window=window
        self.setHeaderHidden(True)
        self.setIndentation(23)
        self.setAnimated(False)
        self.setExpandsOnDoubleClick(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(self.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menu)
        self.itemClicked.connect(self.activate)
        self.itemExpanded.connect(self.remember)
        self.itemCollapsed.connect(self.remember)
        self.currentItemChanged.connect(lambda *_: self.viewport().update())
        self.rebuilding=False

    def remember(self, *_):
        if self.rebuilding or not self.window.vault: return
        self.window.set_vault_pref('expanded', [p for p,i in self.window.folder_items.items() if i.isExpanded()])

    def activate(self,item,column):
        board=item.data(0,BOARD)
        if board:
            self.window.open_board_id(board);return
        name=item.data(0,NOTE)
        if name:
            self.window.focus(name)
        else:
            # Qt already toggles the branch arrow; clicking its text toggles too.
            if self.viewport().mapFromGlobal(self.cursor().pos()).x() >= self.visualItemRect(item).left():
                item.setExpanded(not item.isExpanded())

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Delete:
            self.trash_item(self.currentItem());return
        if event.key()==Qt.Key.Key_F2:
            self.rename(self.currentItem()); return
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):
            item=self.currentItem()
            if item: self.activate(item,0)
            return
        super().keyPressEvent(event)

    def drawBranches(self, painter, rect, index):
        # Paint only vertical ancestry rails and a chevron: no native dotted
        # connectors or branch boxes, matching a compact file explorer.
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected_ancestors = set()
        current = self.currentItem()
        while current is not None:
            selected_ancestors.add(id(current))
            current = current.parent()
        parent = index.parent()
        x = rect.right() - self.indentation() / 2
        while parent.isValid():
            x -= self.indentation()
            active = id(self.itemFromIndex(parent)) in selected_ancestors
            painter.setPen(QPen(QColor('#626069' if active else '#424242'), 1))
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom() + 1))
            parent = parent.parent()
        item = self.itemFromIndex(index)
        if item.data(0, FOLDER) is not None:
            x = rect.right() - self.indentation() / 2
            y = rect.center().y()
            painter.setPen(QPen(QColor('#a09da6' if item.isExpanded() else '#77747c'), 1.7,
                                Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            if item.isExpanded():
                points = [(x-4,y-2),(x,y+2),(x+4,y-2)]
            else:
                points = [(x-2,y-4),(x+2,y),(x-2,y+4)]
            painter.drawLine(QPointF(*points[0]), QPointF(*points[1]))
            painter.drawLine(QPointF(*points[1]), QPointF(*points[2]))
        painter.restore()

    def menu(self,pos):
        item=self.itemAt(pos)
        self.setCurrentItem(item)
        menu=QMenu(self)
        menu.addAction(icon('note'),'Tạo ghi chú tại đây',lambda: self.window.create_in_folder(self.window.selected_folder()))
        menu.addAction(icon('folder-plus'),'Tạo thư mục',self.window.create_folder)
        menu.addAction(icon('board'),'Tạo bảng tại đây',self.window.new_board)
        if item and item.data(0,BOARD):
            menu.addAction('Nhân bản bảng…',lambda:self.duplicate_board(item.data(0,BOARD)))
        if item:
            menu.addSeparator()
            menu.addAction('Đổi tên…    F2',lambda: self.rename(item))
            menu.addAction('Di chuyển đến…',lambda: self.move_dialog(item))
            menu.addAction('Sao chép đường dẫn tương đối',lambda: self.window.copy_path(self.relative(item)))
            menu.addSeparator();menu.addAction('Chuyển vào thùng rác…',lambda:self.trash_item(item))
        menu.exec(self.viewport().mapToGlobal(pos))

    def trash_item(self,item):
        if not item or not self.window.vault:return
        relative=self.relative(item)
        choice=QMessageBox.question(self,'Chuyển vào thùng rác','Chuyển “'+relative+'” vào thùng rác? Có thể khôi phục sau.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if choice!=QMessageBox.StandardButton.Yes:return
        try:
            if not self.window.close_documents() or not self.window.save_layout():return
            from trash import move
            move(self.window.vault,relative)
            self.window.layout_timer.stop();self.window.vault=None
            self.window.load(self.window.current_root)
        except Exception as error:QMessageBox.warning(self,'Không chuyển vào thùng rác được',str(error))

    def restore_item(self):
        if not self.window.vault:return
        from trash import entries,restore
        items=entries(self.window.vault)
        if not items:QMessageBox.information(self,'Thùng rác','Thùng rác đang trống.');return
        labels=[i['original']+' · '+i['time'] for i in items]
        label,ok=QInputDialog.getItem(self,'Khôi phục','Mục cần khôi phục:',labels,0,False)
        if ok:
            try:
                if not self.window.close_documents() or not self.window.save_layout():return
                restore(self.window.vault,items[labels.index(label)]['id'])
                self.window.layout_timer.stop();self.window.vault=None;self.window.load(self.window.current_root)
            except Exception as error:QMessageBox.warning(self,'Không khôi phục được',str(error))

    def duplicate_board(self,identity):
        name,ok=QInputDialog.getText(self,'Nhân bản bảng','Tên bảng mới:',text=self.window.boards.get(identity)['name']+' — Bản sao')
        if ok:
            try:
                if not self.window.save_layout() or not self.window.close_documents():return
                new_id=self.window.boards.duplicate(identity,name.strip(),str(Path(self.window.boards.relative_path(identity)).parent))
                self.window.reload();self.window.open_board_id(new_id)
            except Exception as error:QMessageBox.warning(self,'Không nhân bản được',str(error))

    def relative(self,item):
        return item.data(0,NOTE) or (self.window.boards.relative_path(item.data(0,BOARD)) if item.data(0,BOARD) else item.data(0,FOLDER))

    def rename(self,item):
        if not item: return
        relative=self.relative(item)
        note=bool(item.data(0,NOTE));is_board=bool(item.data(0,BOARD))
        name,ok=QInputDialog.getText(self,'Đổi tên','Tên mới:',text=Path(relative).stem if note or is_board else Path(relative).name)
        if ok:
            try:
                self.window.vault.validate_name(name)
                destination=str(Path(relative).parent/(name.strip()+('.md' if note else '.vlaw' if is_board else '')))
                self.relocate(relative,destination)
            except Exception as error: QMessageBox.warning(self,'Không đổi tên được',str(error))

    def move_dialog(self,item):
        if not item: return
        relative=self.relative(item)
        folders=['']+[f for f in self.window.vault.folders() if f!=relative and not f.startswith(relative+'/')]
        labels=['Gốc vault']+folders[1:]
        chosen,ok=QInputDialog.getItem(self,'Di chuyển','Thư mục đích:',labels,0,False)
        if ok: self.relocate(relative,str(Path(folders[labels.index(chosen)])/Path(relative).name))

    def relocate(self,source,destination):
        try:
            if not self.window.close_documents(): return
            if not self.window.save_layout(): return
            self.window.vault.relocate(source,destination)
            self.window.layout_timer.stop()
            # Do not write the old board paths over the migrated layout on reload.
            self.window.vault=None
            self.window.load(self.window.current_root)
        except Exception as error:
            QMessageBox.warning(self,'Không di chuyển được',str(error))

    def dropEvent(self,event):
        if event.source() is not self: event.ignore(); return
        item=self.currentItem()
        if not item: event.ignore(); return
        target=self.itemAt(event.position().toPoint())
        parent=(target.data(0,FOLDER) if target and target.data(0,FOLDER) is not None else
                str(Path(self.relative(target)).parent) if target else '')
        source=self.relative(item)
        self.relocate(source,str(Path(parent)/Path(source).name))
        event.acceptProposedAction()
