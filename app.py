import sys
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QPointF, QSize
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath, QFont, QIcon, QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsScene, QGraphicsView,
    QGraphicsRectItem, QGraphicsTextItem, QDialog, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QTextBrowser, QPushButton, QLabel, QFileDialog, QMessageBox,
    QInputDialog, QLineEdit, QSplitter, QTreeWidget, QTreeWidgetItem, QWidget, QMenu, QTabBar, QCheckBox, QListWidget, QAbstractItemView, QComboBox, QGraphicsProxyWidget, QDoubleSpinBox)
from live_editor import LiveEditor
from portable_refs import split_references,strip_references
from storage import Vault
from boards import Boards
from relation_types import ensure_categories,relation_label
from card_visuals import COLORS, META, details, with_details, style_for, Pipe, orthogonal_path, TIER_NAMES, TIER_MODULES
from theme import apply_theme
from icons import icon
from explorer import Explorer, ExplorerItem, BOARD
from preferences import Preferences, SettingsDialog, DEFAULT_KEYS

class Card(QGraphicsRectItem):
    def __init__(self, board, name, position):
        super().__init__(0, 0, 260, 104)
        self.board, self.name = board, name
        self.setFlags(self.GraphicsItemFlag.ItemIsMovable | self.GraphicsItemFlag.ItemIsSelectable | self.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.hover_port=None
        self.setAcceptHoverEvents(True)
        self.reload_text()
        self.setToolTip(name + '\nNhấp đúp để đọc / sửa. Kéo để sắp xếp.')
        self.setPos(*position)

    PORTS = {'left':QPointF(0,52),'right':QPointF(260,52),'top':QPointF(130,0),'bottom':QPointF(130,104)}

    def reload_text(self):
        text,_=self.board.window.vault.read(self.name)
        self.title,self.summary=details(text,self.name)
        self.update()

    def boundingRect(self):
        return self.rect().adjusted(-20,-20,20,20)

    def shape(self):
        path=QPainterPath();path.addRect(self.rect())
        for point in self.PORTS.values(): path.addEllipse(point,18,18)
        return path

    def hoverMoveEvent(self,event):
        self.hover_port=next((key for key,point in self.PORTS.items() if (point-event.pos()).manhattanLength()<24),None)
        self.setCursor(Qt.CursorShape.CrossCursor if self.hover_port else Qt.CursorShape.OpenHandCursor)
        self.update()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self,event):
        self.hover_port=None;self.update()
        super().hoverLeaveEvent(event)

    def paint(self, painter, option, widget=None):
        from PyQt6.QtGui import QFontMetricsF
        style=style_for(self.board.window,self.name)
        color=QColor(style['color'])
        selected=self.isSelected()
        path=QPainterPath()
        path.moveTo(10,0);path.lineTo(248,0);path.lineTo(260,12);path.lineTo(260,94)
        path.lineTo(250,104);path.lineTo(0,104);path.lineTo(0,10);path.closeSubpath()
        if selected:
            painter.setPen(QPen(color.darker(210),8));painter.drawPath(path)
        painter.setPen(QPen(color,2 if selected else 1))
        painter.setBrush(QColor('#292832'));painter.drawPath(path)
        painter.setPen(QPen(color.darker(160),1))
        painter.drawLine(QPointF(16,33),QPointF(244,33))
        painter.setPen(color)
        painter.setFont(QFont('Sans Serif',8,QFont.Weight.Bold))
        painter.drawText(16,23,'T'+str(style['tier']))
        painter.setPen(QColor('#88838e'))
        painter.drawText(54,23,TIER_MODULES[style['tier']-1])
        painter.setFont(QFont('Sans Serif',10,QFont.Weight.DemiBold))
        painter.setPen(QColor('#f0edf5'))
        title=QFontMetricsF(painter.font()).elidedText(self.title,Qt.TextElideMode.ElideRight,228)
        painter.drawText(16,55,title)
        painter.setFont(QFont('Sans Serif',9))
        painter.setPen(QColor('#b8b2c0'))
        summary=QFontMetricsF(painter.font()).elidedText(self.summary or 'Nhấp đúp để viết mô tả ngắn…',Qt.TextElideMode.ElideRight,228)
        painter.drawText(16,80,summary)
        painter.setPen(QPen(color.darker(180),1))
        for x in range(30,235,13): painter.drawLine(QPointF(x,99),QPointF(x+6,99))
        for key,point in self.PORTS.items():
            radius=12 if self.hover_port==key else 9
            painter.setBrush(QColor('#1e1e24'));painter.setPen(QPen(color,1.5))
            painter.drawEllipse(point,radius,radius)
            painter.drawLine(point+QPointF(-3,0),point+QPointF(3,0))
            painter.drawLine(point+QPointF(0,-3),point+QPointF(0,3))

    def mousePressEvent(self, event):
        port=next((key for key,point in self.PORTS.items() if (point-event.pos()).manhattanLength()<16),None)
        if event.button() == Qt.MouseButton.LeftButton and port:
            self.board.connecting = self.name
            self.board.source_port = port
            self.board.window.statusBar().showMessage('Kéo đến ghi chú khác để tạo đường nối riêng cho bảng')
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.board.connecting:
            self.board.draw_connection_preview(self.mapToScene(self.PORTS[self.board.source_port]),event.scenePos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.board.connecting:
            source = self.board.connecting
            target = None
            for item in self.board.scene().items(event.scenePos()):
                while item is not None and not isinstance(item, Card):
                    item = item.parentItem()
                if isinstance(item, Card) and item.name != source:
                    target = item.name
                    break
            source_port=self.board.source_port
            target_port=min(self.PORTS,key=lambda key:(self.board.cards[target].mapToScene(self.PORTS[key])-event.scenePos()).manhattanLength()) if target else None
            self.board.cancel_connection()
            if target:
                self.board.window.add_connection(source,target,source_port,target_port)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.board.window.edit(self.name)
        event.accept()

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            self.board.redraw_edges()
            self.board.update_palette_position()
            self.board.window.layout_timer.start()
            if hasattr(self.board,'history'):self.board.history.changed()
        return super().itemChange(change, value)

class Board(QGraphicsView):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.setScene(QGraphicsScene(self))
        self.cards, self.edges = {}, []
        self.connecting = None
        self.rewiring=None
        self.pipe_press=None
        self.connection_preview = None
        self.source_port = 'right'
        self.setMouseTracking(True)
        self.edge_editor=None
        self.edge_click_pair=None;self.edge_click_count=0;self.edge_click_position=None
        self.edge_click_timer=QTimer(self)
        self.edge_click_timer.setSingleShot(True)
        self.edge_click_timer.timeout.connect(self.finish_edge_click)
        self.flow_phase = 0
        self.palette = None
        self.palette_name = None
        self.flow_timer = QTimer(self)
        self.flow_timer.setInterval(40)
        self.flow_timer.timeout.connect(self.animate_pipes)
        self.flow_timer.start()
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Repaint the canvas together while dragging nodes and rerouting edges.
        self.setViewportUpdateMode(self.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(self.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(self.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor('#1e1e1e'))
        self.scene().selectionChanged.connect(self.selection_changed)
        self.setSceneRect(-20000, -20000, 40000, 40000)
        from board_history import BoardHistory
        self.history=BoardHistory(self)
        self.horizontalScrollBar().valueChanged.connect(self.camera_changed)
        self.verticalScrollBar().valueChanged.connect(self.camera_changed)
        self.grabGesture(Qt.GestureType.PinchGesture)

    def port_at(self,position):
        scene_pos=self.mapToScene(position)
        # Use screen-pixel distance for easy clicking even when zoomed out.
        best=None;distance=20
        for name,card in self.cards.items():
            for port,point in Card.PORTS.items():
                pixel=self.mapFromScene(card.mapToScene(point))
                delta=pixel-position
                value=(delta.x()**2+delta.y()**2)**0.5
                if value<distance: best=(name,port);distance=value
        return best

    def begin_rewire(self,pair,endpoint):
        self.cancel_edge_click()
        self.rewiring=(tuple(pair),endpoint)
        self.connecting=None
        self.pipe_press=None
        self.redraw_edges()
        self.window.statusBar().showMessage('Chuyển đầu ống: chọn cổng + khác trên cùng ghi chú • Bấm nền hoặc Esc để hủy')

    def finish_rewire(self,hit):
        if not self.rewiring:return False
        pair,endpoint=self.rewiring
        expected=pair[0] if endpoint=='source' else pair[1]
        if not hit or hit[0]!=expected:return False
        data=self.window.boards.get(self.window.active_board)
        key='\n'.join(pair)
        forward=self.cards[pair[1]].x()>=self.cards[pair[0]].x()
        old=data.setdefault('ports',{}).get(key)
        ports=dict(old or {'source':'right' if forward else 'left','target':'left' if forward else 'right'})
        ports[endpoint]=hit[1]
        data['ports'][key]=ports
        try:self.window.boards.save()
        except Exception as error:
            if old is None:data['ports'].pop(key,None)
            else:data['ports'][key]=old
            QMessageBox.warning(self,'Không lưu được cổng nối',str(error));return False
        self.cancel_connection()
        self.window.statusBar().showMessage('Đã chuyển cổng nối • Giữ nguyên quan hệ, tên và màu')
        return True

    def rewire_preview(self,position):
        pair,endpoint=self.rewiring
        data=self.window.boards.get(self.window.active_board)
        forward=self.cards[pair[1]].x()>=self.cards[pair[0]].x()
        ports=data.get('ports',{}).get('\n'.join(pair),{})
        start=self.cards[pair[0]].mapToScene(Card.PORTS[ports.get('source','right' if forward else 'left')])
        end=self.cards[pair[1]].mapToScene(Card.PORTS[ports.get('target','left' if forward else 'right')])
        cursor=self.mapToScene(position)
        if self.connection_preview:self.scene().removeItem(self.connection_preview)
        path=orthogonal_path(cursor if endpoint=='source' else start,end if endpoint=='source' else cursor,ports.get('source','right' if forward else 'left'))
        self.connection_preview=self.scene().addPath(path,QPen(QColor('#d3b3ff'),3,Qt.PenStyle.DashLine))
        self.connection_preview.setZValue(-0.5)

    def mousePressEvent(self,event):
        self.pipe_press=None
        if self.rewiring and event.button()==Qt.MouseButton.LeftButton:
            hit=self.port_at(event.position().toPoint())
            if not self.finish_rewire(hit) and hit is None:self.cancel_connection()
            event.accept();return
        if event.button()==Qt.MouseButton.LeftButton and not self.connecting:
            item=self.itemAt(event.position().toPoint())
            if isinstance(item,Pipe):
                position=event.position().toPoint()
                start=self.mapFromScene(item.path().pointAtPercent(0));end=self.mapFromScene(item.path().pointAtPercent(1))
                endpoint='source' if (position-start).manhattanLength()<(position-end).manhattanLength() else 'target'
                near=min((position-start).manhattanLength(),(position-end).manhattanLength())<90
                if near:self.pipe_press=(tuple(item.data(0)),endpoint,position)
            if isinstance(item,Pipe) and (self.window.prefs.get('triple_click_unlink',True) or self.pipe_press):
                self.register_edge_click(item.data(0),event.position().toPoint())
                event.accept();return
            self.cancel_edge_click()
        if event.button()==Qt.MouseButton.LeftButton:
            hit=self.port_at(event.position().toPoint())
            if self.connecting:
                if hit and hit[0]!=self.connecting:
                    source,port=self.connecting,self.source_port
                    self.cancel_connection()
                    self.window.add_connection(source,hit[0],port,hit[1])
                elif not hit:
                    self.cancel_connection()
                    self.window.statusBar().showMessage('Đã hủy tạo đường nối')
                event.accept();return
            if hit:
                self.connecting,self.source_port=hit
                self.window.statusBar().showMessage('Chọn cổng + ở đích để nối • Esc hủy • Vẫn có thể giữ chuột và kéo')
                event.accept();return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self,event):
        item=self.itemAt(event.position().toPoint())
        if event.button()==Qt.MouseButton.LeftButton and isinstance(item,Pipe) and self.window.prefs.get('triple_click_unlink',True):
            self.register_edge_click(item.data(0),event.position().toPoint());event.accept();return
        super().mouseDoubleClickEvent(event)

    def cancel_edge_click(self):
        self.edge_click_timer.stop();self.edge_click_pair=None;self.edge_click_count=0

    def register_edge_click(self,pair,position):
        pair=tuple(pair)
        near=self.edge_click_position is not None and (position-self.edge_click_position).manhattanLength()<=QApplication.startDragDistance()*2
        if self.edge_click_timer.isActive() and self.edge_click_pair==pair and near:
            self.edge_click_count+=1
        else:self.edge_click_count=1
        self.edge_click_pair=pair;self.edge_click_position=position
        if self.edge_click_count>=3 and self.window.prefs.get('triple_click_unlink',True):
            self.cancel_edge_click()
            if self.edge_editor:self.edge_editor.close()
            self.window.remove_connection(pair)
            self.window.statusBar().showMessage('Đã bỏ liên kết bằng 3 lần bấm • Tệp ghi chú được giữ nguyên')
        else:self.edge_click_timer.start(QApplication.doubleClickInterval())

    def finish_edge_click(self):
        pair=self.edge_click_pair;self.cancel_edge_click()
        if pair in self.window.connections:self.edit_connection(pair)

    def mouseMoveEvent(self,event):
        if self.pipe_press and event.buttons() & Qt.MouseButton.LeftButton:
            pair,endpoint,start=self.pipe_press
            if (event.position().toPoint()-start).manhattanLength()>QApplication.startDragDistance():
                self.begin_rewire(pair,endpoint)
        if self.rewiring:
            self.rewire_preview(event.position().toPoint());event.accept();return
        if self.connecting:
            card=self.cards.get(self.connecting)
            if card:
                self.draw_connection_preview(card.mapToScene(Card.PORTS[self.source_port]),self.mapToScene(event.position().toPoint()))
            event.accept();return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        self.pipe_press=None
        if self.rewiring and event.button()==Qt.MouseButton.LeftButton:
            self.finish_rewire(self.port_at(event.position().toPoint()))
            event.accept();return
        if self.connecting and event.button()==Qt.MouseButton.LeftButton:
            hit=self.port_at(event.position().toPoint())
            if hit and hit[0]!=self.connecting:
                source,port=self.connecting,self.source_port
                self.cancel_connection()
                self.window.add_connection(source,hit[0],port,hit[1])
            event.accept();return
        super().mouseReleaseEvent(event)

    def edit_connection(self,pair):
        if self.edge_editor:
            self.edge_editor.close()
        self.show_palette(None)
        data=self.window.boards.get(self.window.active_board)
        key='\n'.join(pair)
        original=data.get('edge_styles',{}).get(key,{})
        ensure_categories(data)
        dialog=QDialog(self.window)
        dialog.setWindowTitle('Tùy chỉnh liên kết');dialog.resize(480,220)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel(Path(pair[0]).stem+' → '+Path(pair[1]).stem))
        label=QLineEdit(original.get('label',''));label.setMaxLength(200)
        label.setPlaceholderText('Ghi chú riêng dưới đường ống, ví dụ: hello…')
        show_note=QCheckBox('Hiện ô ghi chú riêng bên dưới đường ống')
        show_note.setChecked(original.get('show_note',bool(original.get('label'))))
        layout.addWidget(show_note);layout.addWidget(label)
        layout.addWidget(QLabel('Phân loại quan hệ — hiển thị phía trên đường ống'))
        category_fields={}
        for category in data['relation_categories']:
            field=QCheckBox(category['name'])
            field.setChecked(category['id'] in data.get('edge_categories',{}).get(key,[]))
            category_fields[category['id']]=field;layout.addWidget(field)
        routing=QComboBox();routing.addItem('Tự động: ngang / dọc / chữ L','circuit')
        routing.setCurrentIndex(max(0,routing.findData(original.get('routing','straight'))))
        layout.addWidget(routing)
        colors=QHBoxLayout();chosen={'color':original.get('color','')}
        current=QLabel('Màu: '+(chosen['color'] or 'theo thẻ nguồn'));layout.addWidget(current)
        for color in COLORS:
            button=QPushButton();button.setFixedSize(24,24)
            button.setStyleSheet('background:'+color+';border-radius:5px;')
            def select(checked=False,c=color):
                chosen['color']=c;current.setText('Màu: '+c)
            button.clicked.connect(select);colors.addWidget(button)
        layout.addLayout(colors)
        inherit=QPushButton('Dùng màu thẻ nguồn')
        inherit.clicked.connect(lambda:(chosen.update(color=''),current.setText('Màu: theo thẻ nguồn')))
        layout.addWidget(inherit)
        save=QPushButton('Lưu liên kết');save.setObjectName('primary');layout.addWidget(save)
        def commit():
            try:
                data.setdefault('edge_categories',{})[key]=[identity for identity,field in category_fields.items() if field.isChecked()]
                data.setdefault('edge_styles',{})[key]={'label':label.text().strip(),'show_note':show_note.isChecked(),'color':chosen['color'],'routing':routing.currentData()}
                self.window.boards.save();self.redraw_edges()
                for document in self.window.documents.values():document.refresh_relations()
                dialog.accept()
            except Exception as error: QMessageBox.warning(dialog,'Chưa lưu được',str(error))
        save.clicked.connect(commit)
        dialog.category_fields=category_fields
        dialog.show_note_field=show_note
        dialog.label_field=label;dialog.routing_field=routing;dialog.chosen=chosen;dialog.commit=commit
        self.edge_editor=dialog
        dialog.show()

    def animate_pipes(self):
        if not self.isVisible() or not self.edges: return
        if hasattr(self.window,'desk') and self.window.desk.area.isVisible():return
        self.flow_phase=(self.flow_phase+1.8)%100000
        for edge in self.edges: edge.update()

    def update_palette_position(self):
        if self.palette and self.palette_name in self.cards:
            card=self.cards[self.palette_name]
            self.palette.setPos(card.pos()+QPointF(-30,126))

    def set_style(self,name,tier=None,color=None):
        data=self.window.boards.get(self.window.active_board)
        style=data.setdefault('styles',{}).setdefault(name,style_for(self.window,name))
        if tier is not None:
            style['tier']=tier
            style['color']=COLORS[tier-1]
            style['custom_color']=False
        if color is not None: style['color']=color;style['custom_color']=True
        self.window.boards.save()
        self.cards[name].update()
        self.redraw_edges()

    def show_palette(self,name):
        if self.palette:
            self.scene().removeItem(self.palette)
            self.palette=None
        self.palette_name=name
        if not name: return
        widget=QWidget(); widget.setObjectName('cardPalette')
        layout=QVBoxLayout(widget);layout.setContentsMargins(10,8,10,8)
        row=QHBoxLayout()
        row.addWidget(QLabel('Bậc'))
        tier=QComboBox();tier.addItems(['T'+str(i)+' · '+TIER_MODULES[i-1].replace(' MODULE','').title()+' · '+TIER_NAMES[i-1] for i in range(1,11)])
        tier.setCurrentIndex(style_for(self.window,name)['tier']-1)
        tier.currentIndexChanged.connect(lambda index:self.set_style(name,tier=index+1))
        row.addWidget(tier);row.addWidget(QLabel('T1 cao nhất → T10'))
        layout.addLayout(row)
        colors=QHBoxLayout()
        for color in COLORS:
            button=QPushButton();button.setFixedSize(22,22)
            button.setStyleSheet('background:'+color+';border:1px solid #bbb;border-radius:5px; padding:0;')
            button.setToolTip(color)
            button.clicked.connect(lambda checked=False,c=color:self.set_style(name,color=c))
            colors.addWidget(button)
        layout.addLayout(colors)
        self.palette=self.scene().addWidget(widget)
        self.palette.setZValue(50)
        self.update_palette_position()

    def draw_connection_preview(self,a,b):
        if self.connection_preview:
            self.scene().removeItem(self.connection_preview)
        path = orthogonal_path(a,b,self.source_port)
        self.connection_preview = self.scene().addPath(path,QPen(QColor('#c5a7ff'),2,Qt.PenStyle.DashLine))
        self.connection_preview.setZValue(-0.5)

    def cancel_connection(self):
        was_rewiring=self.rewiring is not None
        self.rewiring=None;self.pipe_press=None
        if self.connection_preview:
            self.scene().removeItem(self.connection_preview)
        self.connection_preview = None
        self.connecting = None
        if was_rewiring:self.redraw_edges()

    def keyPressEvent(self,event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key()==Qt.Key.Key_Z:self.history.step(-1);event.accept();return
            if event.key()==Qt.Key.Key_Y:self.history.step(1);event.accept();return
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_connection()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self,event):
        item = self.itemAt(event.pos())
        menu = QMenu(self)
        hit=self.port_at(event.pos())
        if hit:
            board=self.window.boards.get(self.window.active_board)
            for pair in self.window.connections:
                forward=self.cards[pair[1]].x()>=self.cards[pair[0]].x()
                ports=board.get('ports',{}).get('\n'.join(pair),{})
                for endpoint,node,default in [('source',pair[0],'right' if forward else 'left'),('target',pair[1],'left' if forward else 'right')]:
                    if node==hit[0] and ports.get(endpoint,default)==hit[1]:
                        menu.addAction('Chuyển đầu ống: '+Path(pair[0]).stem+' → '+Path(pair[1]).stem,lambda checked=False,p=pair,e=endpoint:self.begin_rewire(p,e))
            if not menu.isEmpty():menu.addSeparator()
        if item in self.edges:
            pair = item.data(0)
            menu.addAction('Chuyển cổng nguồn…',lambda:self.begin_rewire(pair,'source'))
            menu.addAction('Chuyển cổng đích…',lambda:self.begin_rewire(pair,'target'))
            menu.addAction('Xóa đường nối khỏi bảng',lambda: self.window.remove_connection(pair))
        else:
            while item and not isinstance(item,Card): item=item.parentItem()
            if isinstance(item,Card):
                menu.addAction('Bỏ ghi chú khỏi bảng (giữ tệp)',lambda: self.window.remove_from_board(item.name))
            else:
                menu.addAction('Thêm ghi chú / thư mục…',self.window.add_notes_dialog)
        menu.exec(event.globalPos())

    def selection_changed(self):
        for card in self.cards.values():
            card.update()
        self.redraw_edges()
        chosen=[c for c in self.scene().selectedItems() if isinstance(c,Card)]
        self.show_palette(chosen[0].name if len(chosen)==1 else None)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        painter.setPen(QPen(QColor('#343136'), 1))
        if not self.window.prefs.get("grid", True):
            return
        step = 32
        while step*self.transform().m11()<16:step*=2
        for x in range(int(rect.left()) // step * step, int(rect.right()) + step, step):
            for y in range(int(rect.top()) // step * step, int(rect.bottom()) + step, step):
                painter.drawPoint(QPointF(x, y))

    def camera_changed(self,*_):
        self.history.changed()
        if self.window.boards and not self.history.restoring:self.window.layout_timer.start()

    def set_zoom(self,scale,anchor=None):
        scale=max(0.01,min(3.0,scale))
        if anchor is None:anchor=self.viewport().rect().center()
        before=self.mapToScene(anchor)
        self.setTransformationAnchor(self.ViewportAnchor.NoAnchor)
        self.scale(scale/self.transform().m11(),scale/self.transform().m11())
        after=self.mapToScene(anchor)
        self.translate(after.x()-before.x(),after.y()-before.y())
        self.window.update_zoom_display();self.history.changed()

    def wheelEvent(self,event):
        pixel=event.pixelDelta();angle=event.angleDelta()
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta=pixel.y() if not pixel.isNull() else angle.y()
            self.set_zoom(self.transform().m11()*pow(1.0012,delta*0.45),event.position().toPoint())
        else:
            dx=pixel.x() if not pixel.isNull() else angle.x()/2
            dy=pixel.y() if not pixel.isNull() else angle.y()/2
            # Keep subpixel movement from high resolution touchpads.
            if not hasattr(self,'pan_residual'):self.pan_residual=[0.0,0.0]
            for index,(bar,delta) in enumerate([(self.horizontalScrollBar(),dx),(self.verticalScrollBar(),dy)]):
                value=self.pan_residual[index]+delta*0.60;whole=int(value)
                self.pan_residual[index]=value-whole;bar.setValue(bar.value()-whole)
            self.history.changed()
        event.accept()

    def viewportEvent(self,event):
        from PyQt6.QtCore import QEvent
        if event.type()==QEvent.Type.NativeGesture:
            if event.gestureType()==Qt.NativeGestureType.ZoomNativeGesture:
                self.set_zoom(self.transform().m11()*pow(2.718281828,event.value()*0.45),event.position().toPoint())
                event.accept();return True
        return super().viewportEvent(event)

    def event(self,event):
        from PyQt6.QtCore import QEvent
        if event.type()==QEvent.Type.Gesture:
            gesture=event.gesture(Qt.GestureType.PinchGesture)
            if gesture:
                if gesture.changeFlags() & gesture.ChangeFlag.ScaleFactorChanged:
                    factor=gesture.scaleFactor()/max(gesture.lastScaleFactor(),0.001)
                    self.set_zoom(self.transform().m11()*pow(factor,0.45))
                event.accept();return True
        return super().event(event)

    def redraw_edges(self):
        for edge in self.edges:
            self.scene().removeItem(edge)
        self.edges = []
        for source, target in self.window.connections:
            if source not in self.cards or target not in self.cards:
                continue
            left, right = self.cards[source], self.cards[target]
            forward = right.x() >= left.x()
            edge_key=source+'\n'+target
            ports=self.window.boards.get(self.window.active_board).get('ports',{}).get(edge_key,{})
            a = left.mapToScene(Card.PORTS[ports.get('source','right' if forward else 'left')])
            b = right.mapToScene(Card.PORTS[ports.get('target','left' if forward else 'right')])
            source_side=ports.get('source','right' if forward else 'left')
            path=orthogonal_path(a,b,source_side)
            # Prefer the other L orientation if the first would enter a card body.
            from PyQt6.QtGui import QPainterPathStroker
            stroker=QPainterPathStroker();stroker.setWidth(1)
            bodies=QPainterPath()
            bodies.addRect(left.mapRectToScene(left.rect().adjusted(2,2,-2,-2)))
            bodies.addRect(right.mapRectToScene(right.rect().adjusted(2,2,-2,-2)))
            if stroker.createStroke(path).intersects(bodies):
                alternative=orthogonal_path(a,b,'right' if source_side in ('top','bottom') else 'bottom')
                if not stroker.createStroke(alternative).intersects(bodies):path=alternative
            edge_style=self.window.boards.get(self.window.active_board).get('edge_styles',{}).get(edge_key,{})
            selected = {c.name for c in self.scene().selectedItems() if isinstance(c, Card)}
            active = source in selected or target in selected
            item = Pipe(path,edge_style.get('color') or style_for(self.window,source)['color'],self,relation_label(self.window.boards.get(self.window.active_board),(source,target)),edge_style.get('label','') if edge_style.get('show_note',bool(edge_style.get('label'))) else '')
            self.scene().addItem(item)
            item.setZValue(-1)
            item.setToolTip(source+' → '+target+'\n'+item.label+('\n'+edge_style['label'] if edge_style.get('label') else '')+'\nChuột phải để sửa hoặc xóa đường nối')
            item.setData(0,(source,target))
            if self.rewiring and self.rewiring[0]==(source,target):item.setVisible(False)
            self.edges.append(item)

class Editor(QDialog):
    def __init__(self, window, name):
        super().__init__(window)
        self.window, self.name = window, name
        text, self.revision = window.vault.read(name)
        self.original_core=strip_references(text)
        self.saved_source=META.sub('',self.original_core)
        self.metadata=''.join(m[0] for m in META.finditer(self.original_core))
        self.setWindowTitle(name + ' — Vision law')
        self.resize(920, 640)
        layout = QVBoxLayout(self)
        heading = QLabel(Path(name).stem)
        self.heading_label=heading
        heading.setObjectName('heading')
        layout.addWidget(heading)
        self.card_title,self.card_summary=details(text,name)
        self.title_field=QLineEdit(self.card_title)
        self.title_field.setPlaceholderText('Tiêu đề thẻ')
        self.summary_field=QLineEdit(self.card_summary)
        self.summary_field.setPlaceholderText('Viết một câu mô tả ngắn cho thẻ…')
        layout.addWidget(self.title_field)
        layout.addWidget(self.summary_field)
        crumb = QLabel('GHI CHÚ  /  ' + name)
        crumb.setObjectName('muted')
        layout.addWidget(crumb)
        panes = QSplitter()
        self.panes=panes
        self.input = LiveEditor(self.saved_source)
        self.preview = QTextBrowser()
        self.preview.setOpenLinks(False)
        self.preview.anchorClicked.connect(self.follow)
        self.preview.setVisible(False)
        panes.addWidget(self.input)
        panes.addWidget(self.preview)
        editing_tools=QHBoxLayout()
        for title,callback in [('Đậm',lambda:self.input.wrap('**')),('Nghiêng',lambda:self.input.wrap('*'))]:
            button=QPushButton(title);button.clicked.connect(callback);editing_tools.addWidget(button)
        extra_format=QComboBox();extra_format.addItems(['Định dạng…','Gạch chân','Gạch bỏ','Tô sáng','Mã'])
        extra_format.activated.connect(lambda index:self.input.wrap(['','<u>','~~','==','`'][index]) if index else None)
        editing_tools.addWidget(extra_format)
        heading_choice=QComboBox();heading_choice.addItems(['Tiêu đề…','H1','H2','H3','H4','H5','H6'])
        heading_choice.activated.connect(lambda index:self.input.heading(index) if index else None)
        editing_tools.addWidget(heading_choice);editing_tools.addStretch()
        layout.addLayout(editing_tools)
        layout.addWidget(panes, 1)
        self.source_toggle = QCheckBox('Chế độ đọc')
        self.source_toggle.toggled.connect(lambda reading: (self.input.setVisible(not reading),self.preview.setVisible(reading)))
        self.read_shortcut=QShortcut(QKeySequence('Ctrl+E'),self)
        self.read_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.read_shortcut.activated.connect(lambda:self.source_toggle.setChecked(not self.source_toggle.isChecked()))
        self.input.installEventFilter(self);self.preview.installEventFilter(self)
        layout.addWidget(self.source_toggle)
        self.message = QLabel('Ctrl+B đậm · Ctrl+I nghiêng · Ctrl+1–6 tiêu đề · Ctrl+S lưu')
        layout.addWidget(self.message)
        save = QPushButton('Lưu ghi chú (Ctrl+S)')
        save.setObjectName('primary')
        save.setShortcut('Ctrl+S')
        save.clicked.connect(self.save)
        layout.addWidget(save)
        size = window.prefs.get('editor_size', 15)
        for pane in (self.input, self.preview):
            pane.setStyleSheet(f'font-size: {size}px;')
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(2000)
        self.autosave_timer.timeout.connect(self.save)
        self.title_field.textChanged.connect(self.changed)
        self.summary_field.textChanged.connect(self.changed)
        self.input.textChanged.connect(self.changed)
        self.input.textChanged.connect(self.render)
        self.render()
        self.input.document().setModified(False)

    def eventFilter(self,obj,event):
        from PyQt6.QtCore import QEvent
        if obj in (getattr(self,'input',None),getattr(self,'preview',None)) and event.type() in (QEvent.Type.ShortcutOverride,QEvent.Type.KeyPress):
            if event.key()==Qt.Key.Key_E and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if event.type()==QEvent.Type.KeyPress:
                    reading=not self.source_toggle.isChecked();self.source_toggle.setChecked(reading)
                    (self.preview if reading else self.input).setFocus()
                event.accept();return True
        return super().eventFilter(obj,event)

    def changed(self):
        dirty=self.input.toPlainText()!=self.saved_source or self.title_field.text()!=self.card_title or self.summary_field.text()!=self.card_summary
        if dirty and self.window.prefs.get('autosave', False):
            self.autosave_timer.start()

    def render(self):
        import re
        # Hide legacy wikilinks in reading view; keep the original source intact.
        text = re.sub(r'!?\[\[[^\]]+\]\]', '', META.sub('',strip_references(self.input.toPlainText())))
        from reading_view import render_markdown
        render_markdown(self.preview,text)

    def follow(self, url):
        if url.scheme() == 'vision':
            target = self.window.vault.resolve(url.toString()[7:].replace('%20', ' ').split('#')[0], self.name, self.window.names)
            if target:
                self.window.edit(target)
            else:
                QMessageBox.information(self, 'Liên kết', 'Không tìm thấy ghi chú hoặc tên đang trùng nhau.')

    def save(self):
        self.autosave_timer.stop()
        try:
            current,current_revision=self.window.vault.read(self.name)
            current_core,current_references=split_references(current)
            if current_revision!=self.revision and current_core==self.original_core:self.revision=current_revision
            prefix=getattr(self,'body_heading_prefix','')
            if prefix and self.title_field.text()!=self.card_title:
                prefix='# '+self.title_field.text()+'\n\n'
                self.body_heading_prefix=prefix
            text=self.metadata+prefix+self.input.toPlainText()
            if self.title_field.text()!=self.card_title or self.summary_field.text()!=self.card_summary:
                text=with_details(text,self.title_field.text(),self.summary_field.text())
            text+=current_references
            self.revision = self.window.vault.save(self.name, text, self.revision)
            self.original_core=strip_references(text)
            self.saved_source=META.sub('',self.original_core)
            if prefix and self.saved_source.startswith(prefix):self.saved_source=self.saved_source[len(prefix):]
            self.metadata=''.join(m[0] for m in META.finditer(text))
            self.card_title,self.card_summary=details(text,self.name)
            self.input.blockSignals(True);self.input.setPlainText(self.saved_source);self.input.blockSignals(False)
            self.render()
            if self.name in self.window.board.cards: self.window.board.cards[self.name].reload_text()
            self.input.document().setModified(False)
            self.message.setText('Đã lưu vào tệp Markdown. Bản trước nằm trong .vision-law/backups.')
            self.window.refresh_links()
            return True
        except Exception as error:
            QMessageBox.warning(self, 'Chưa lưu được', str(error))
            return False

    def closeEvent(self, event):
        self.autosave_timer.stop()
        if self.input.toPlainText()!=self.saved_source or self.input.document().isModified() or self.title_field.text()!=self.card_title or self.summary_field.text()!=self.card_summary:
            choice = QMessageBox.question(self, 'Nội dung chưa lưu', 'Lưu thay đổi trước khi đóng?', QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if choice == QMessageBox.StandardButton.Cancel or (choice == QMessageBox.StandardButton.Save and not self.save()):
                event.ignore()
                return
        event.accept()

class Window(QMainWindow):
    def __init__(self, root=None):
        super().__init__()
        self.documents = {}
        self.document_order = []
        self.current_document = None
        self.prefs = Preferences()
        self.shortcuts = []
        self._vault_lease=None
        self.vault = None
        self.boards = None
        self.active_board = None
        self.changing_tabs = False
        self.names, self.connections = [], []
        self.setWindowTitle('Vision law — Không gian kiến thức')
        self.resize(1380, 850)
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.setInterval(500)
        self.layout_timer.timeout.connect(self.save_layout)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        ribbon = QWidget()
        ribbon.setObjectName('ribbon')
        ribbon.setFixedWidth(46)
        rail = QVBoxLayout(ribbon)
        rail.setContentsMargins(4, 10, 4, 8)
        logo=QPushButton();logo.setIcon(QIcon(str(Path(__file__).parent/'assets/vision-law.svg')))
        logo.setIconSize(QSize(28,28));logo.setFixedSize(36,36);logo.setToolTip('Vision law · Đổi vault')
        logo.clicked.connect(self.vault_menu);rail.addWidget(logo)
        for symbol, tip, action in [('folder', 'Đổi vault', self.vault_menu), ('search', 'Tìm ghi chú', lambda: self.search.setFocus()), ('note', 'Tạo ghi chú', self.create), ('board', 'Xem toàn cảnh', self.fit)]:
            rail.addWidget(self.icon_button(symbol, tip, action))
        rail.addStretch()
        self.sidebar_rail_toggle=self.icon_button('sidebar','Ẩn/hiện cột thư mục',self.toggle_sidebar)
        rail.addWidget(self.sidebar_rail_toggle)
        rail.addWidget(self.icon_button('settings', 'Cài đặt', self.settings))
        layout.addWidget(ribbon)
        split = QSplitter()
        sidebar = QWidget()
        self.note_sidebar=sidebar
        self.sidebar_split=split
        self.sidebar_width=260
        sidebar.setObjectName('sidebar')
        sidebar.setMinimumWidth(210)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(10, 10, 10, 10)
        tools = QHBoxLayout()
        for symbol, tip, action in [('note', 'Tạo ghi chú', self.create), ('folder-plus', 'Tạo thư mục', self.create_folder), ('refresh', 'Tải lại từ đĩa', self.reload), ('collapse', 'Thu gọn thư mục', lambda: self.list.collapseAll())]:
            tools.addWidget(self.icon_button(symbol, tip, action))
        tools.addStretch()
        side.addLayout(tools)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Tìm ghi chú…')
        self.search.textChanged.connect(self.filter)
        side.addWidget(self.search)
        self.list = Explorer(self)
        side.addWidget(self.list)
        footer = QHBoxLayout()
        self.vault_label = QPushButton('Chưa mở vault')
        self.vault_label.setIcon(icon('chevrons'))
        self.vault_label.setStyleSheet('text-align: left; padding-left: 0;')
        self.vault_label.clicked.connect(self.vault_menu)
        footer.addWidget(self.vault_label, 1)
        footer.addWidget(self.icon_button('sidebar', 'Ẩn cột thư mục', self.toggle_sidebar))
        side.addLayout(footer)
        split.addWidget(sidebar)
        workspace = QWidget()
        work = QVBoxLayout(workspace)
        work.setContentsMargins(0, 0, 0, 0)
        work.setSpacing(0)
        tabbar = QWidget()
        tabbar.setObjectName('tabbar')
        tabs = QHBoxLayout(tabbar)
        tabs.setContentsMargins(0, 0, 8, 0)
        self.tabs = QTabBar()
        self.tabs.setMinimumHeight(44)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setExpanding(False)
        self.tabs.currentChanged.connect(self.switch_tab)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.tabBarDoubleClicked.connect(self.rename_board)
        self.tabs.tabMoved.connect(self.tabs_reordered)
        tabs.addWidget(self.tabs,1)
        new_tab = QPushButton('＋')
        new_tab.setToolTip('Tạo bảng trắng mới')
        new_tab.clicked.connect(self.new_board)
        tabs.addWidget(new_tab)
        open_tab = QPushButton('Mở bảng')
        open_tab.clicked.connect(self.open_board)
        tabs.addWidget(open_tab)
        work.addWidget(tabbar)
        board_tools = QHBoxLayout()
        board_tools.setContentsMargins(18, 8, 18, 8)
        hint = QLabel('Bảng kiến thức  /  Vault')
        hint.setObjectName('muted')
        board_tools.addWidget(hint)
        board_tools.addStretch()
        for text, action in [('Thêm từ thư mục', self.add_notes_dialog), ('＋ Ghi chú', self.create), ('⤢ Toàn cảnh', self.fit)]:
            button = QPushButton(text)
            button.clicked.connect(action)
            board_tools.addWidget(button)
        zoom_out=QPushButton('−');zoom_out.setToolTip('Thu nhỏ');zoom_out.clicked.connect(lambda:(self.board.set_zoom(self.board.transform().m11()/1.10),self.board.setFocus()))
        board_tools.addWidget(zoom_out)
        self.zoom_display=QDoubleSpinBox();self.zoom_display.setRange(1,300);self.zoom_display.setDecimals(0);self.zoom_display.setSuffix('%');self.zoom_display.setValue(100);self.zoom_display.setFixedWidth(85)
        self.zoom_display.setToolTip('Tỷ lệ thu phóng • Nhập 100 để về kích thước gốc')
        self.zoom_display.editingFinished.connect(lambda:(self.board.set_zoom(self.zoom_display.value()/100),self.board.setFocus()))
        board_tools.addWidget(self.zoom_display)
        zoom_in=QPushButton('+');zoom_in.setToolTip('Phóng to');zoom_in.clicked.connect(lambda:(self.board.set_zoom(self.board.transform().m11()*1.10),self.board.setFocus()))
        board_tools.addWidget(zoom_in)
        work.addLayout(board_tools)
        self.board = Board(self)
        work.addWidget(self.board)
        split.addWidget(workspace)
        split.setSizes([260, 1074])
        layout.addWidget(split)
        self.statusBar().showMessage('Mở vault để bắt đầu • Nhấp đúp nút để sửa • Kéo nền để di chuyển • Cuộn để zoom')
        self.apply_shortcuts()
        from note_windows import DocumentDesk
        self.desk=DocumentDesk(self)
        from page_switcher import PageSwitcher
        self.page_switcher=PageSwitcher(self)
        self.board_undo_shortcuts=[]
        for sequence,direction in [('Ctrl+Z',-1),('Ctrl+Y',1)]:
            shortcut=QShortcut(QKeySequence(sequence),self)
            shortcut.activated.connect(lambda step=direction:self.board.history.step(step) if not self.desk.area.isVisible() else None)
            self.board_undo_shortcuts.append(shortcut)
        if root:
            self.load(root)

    def toggle_sidebar(self):
        if self.note_sidebar.isHidden():
            self.note_sidebar.show()
            total=sum(self.sidebar_split.sizes())
            self.sidebar_split.setSizes([self.sidebar_width,max(1,total-self.sidebar_width)])
            self.sidebar_rail_toggle.setToolTip('Ẩn cột thư mục')
        else:
            self.sidebar_width=max(210,self.note_sidebar.width())
            self.note_sidebar.hide()
            self.sidebar_rail_toggle.setToolTip('Hiện cột thư mục')

    def icon_button(self, name, tip, action):
        button = QPushButton()
        button.setIcon(icon(name))
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setFixedSize(32, 32)
        button.clicked.connect(action)
        return button

    def apply_shortcuts(self):
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.shortcuts = []
        for key, callback in [('new', self.create), ('folder', self.create_folder), ('search', lambda: self.search.setFocus()), ('vault', self.vault_menu), ('settings', self.settings)]:
            shortcut = QShortcut(QKeySequence(self.prefs.get('key_'+key, DEFAULT_KEYS[key])), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)

    def vault_pref_key(self, key):
        import hashlib
        identity = hashlib.sha256(str(self.vault.root).encode()).hexdigest() if self.vault else 'none'
        return 'vaults/' + identity + '/' + key

    def vault_pref(self, key, default):
        return self.prefs.get(self.vault_pref_key(key), default)

    def set_vault_pref(self, key, value):
        self.prefs.set(self.vault_pref_key(key), value)

    def settings(self):
        SettingsDialog(self).exec()

    def selected_folder(self):
        item = self.list.currentItem()
        if item is None:
            return ''
        note = item.data(0, Qt.ItemDataRole.UserRole)
        if item.data(0,BOARD):note=self.boards.relative_path(item.data(0,BOARD))
        if note:
            parent = str(Path(note).parent)
            return '' if parent == '.' else parent
        return item.data(0, Qt.ItemDataRole.UserRole + 1) or ''

    def create_folder(self):
        if not self.vault:
            self.open_vault()
        if not self.vault:
            return
        parent = self.selected_folder()
        name, ok = QInputDialog.getText(self, 'Tạo thư mục', 'Tên thư mục trong ' + (parent or 'gốc vault') + ':')
        if ok:
            try:
                self.vault.create_folder(name, parent)
                self.reload()
            except Exception as error:
                QMessageBox.warning(self, 'Không tạo được thư mục', str(error))

    def vault_menu(self):
        menu = QMenu(self)
        menu.addAction(icon('folder'), 'Mở vault khác…', self.open_vault)
        menu.addAction(icon('folder-plus'), 'Tạo vault mới…', self.new_vault)
        recent = self.prefs.get('recent_vaults', [])
        if recent:
            menu.addSeparator()
        for root in recent:
            action = menu.addAction(Path(root).name + ' — ' + root)
            action.triggered.connect(lambda checked=False, path=root: self.load(path))
        menu.exec(self.vault_label.mapToGlobal(self.vault_label.rect().topLeft()))

    def new_vault(self):
        parent = QFileDialog.getExistingDirectory(self, 'Chọn nơi chứa vault mới')
        if not parent:
            return
        name, ok = QInputDialog.getText(self, 'Tạo vault', 'Tên vault:')
        if ok:
            try:
                Vault.validate_name(name)
                root = Path(parent) / name.strip()
                root.mkdir(exist_ok=False)
                self.load(root)
            except Exception as error:
                QMessageBox.warning(self, 'Không tạo được vault', str(error))

    def open_vault(self):
        root = QFileDialog.getExistingDirectory(self, 'Mở thư mục làm vault')
        if root:
            self.load(root)

    def load(self, root, preserve_documents=False, skip_save=False):
        if not preserve_documents and not self.close_documents(): return
        new_lease=None
        try:
            if self.vault and hasattr(self.board,'history'):
                self.board.history.tim.stop();self.board.history.commit()
            vault = Vault(root)
            from vault_lock import VaultLease
            if self._vault_lease is None or self._vault_lease.root!=vault.root:
                new_lease=VaultLease(vault.root)
            if self.vault and not skip_save and self.vault.root == vault.root and not self.save_layout():
                return
            board_store = Boards(vault)
            board_id = board_store.data.get("active") or board_store.data["boards"][0]["id"]
            board_data = board_store.get(board_id)
            positions = board_data["positions"]
            names = vault.notes()
            # Read before replacing the visible vault; failures leave it intact.
            for name in names:
                vault.read(name)
            if self.vault and not skip_save and not self.save_layout():
                return
            if new_lease:
                if self._vault_lease:self._vault_lease.release()
                self._vault_lease=new_lease;new_lease=None
            self.vault, self.names = vault, names
            self.boards, self.active_board = board_store, board_id
            self.boards.on_change=self.board.history.changed
            self.current_root = vault.root
            self.list.rebuilding = True
            self.layout_timer.stop()
            self.board.cancel_connection()
            self.board.cancel_edge_click()
            if self.board.edge_editor: self.board.edge_editor.close()
            self.board.show_palette(None)
            self.board.cards, self.board.edges = {}, []
            self.board.scene().clear()
            self.list.clear()
            self.tree_items = {}
            folders = {}
            self.folder_items = folders
            for folder_path in vault.folders():
                parent = self.list.invisibleRootItem()
                prefix = ''
                for part in Path(folder_path).parts:
                    prefix = str(Path(prefix) / part)
                    if prefix not in folders:
                        item = ExplorerItem(parent, [part])
                        item.setData(0, Qt.ItemDataRole.UserRole + 1, prefix)
                        item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

                        folders[prefix] = item
                    parent = folders[prefix]
            self.vault_label.setText(vault.root.name)
            recent = [str(vault.root)] + [r for r in self.prefs.get("recent_vaults", []) if r != str(vault.root)]
            self.prefs.set("recent_vaults", recent[:8])
            for i, name in enumerate(names):
                pos = positions.get(name, [(i % 3) * 310, (i // 3) * 180])
                if not isinstance(pos, list) or len(pos) != 2 or not all(isinstance(v, (int, float)) for v in pos):
                    pos = [(i % 3) * 310, (i // 3) * 180]
                if name in positions:
                    card = Card(self.board, name, pos)
                    self.board.cards[name] = card
                    self.board.scene().addItem(card)
                parent = self.list.invisibleRootItem()
                prefix = ''
                for folder in Path(name).parts[:-1]:
                    prefix = str(Path(prefix) / folder)
                    if prefix not in folders:
                        folders[prefix] = ExplorerItem(parent, [folder])
                    parent = folders[prefix]
                item = ExplorerItem(parent, [Path(name).stem])
                item.setData(0, Qt.ItemDataRole.UserRole, name)
                item.setToolTip(0, name)
                self.tree_items[name] = item
            self.board_tree_items={}
            for entry in self.boards.data['boards']:
                relative=self.boards.relative_path(entry['id']);parent=self.list.invisibleRootItem();prefix=''
                for folder in Path(relative).parts[:-1]:
                    prefix=str(Path(prefix)/folder)
                    if prefix not in folders:
                        folders[prefix]=ExplorerItem(parent,[folder]);folders[prefix].setData(0,Qt.ItemDataRole.UserRole+1,prefix)
                    parent=folders[prefix]
                item=ExplorerItem(parent,[Path(relative).stem]);item.setIcon(0,icon('board'));item.setData(0,BOARD,entry['id']);item.setToolTip(0,relative)
                self.board_tree_items[entry['id']]=item
            self.list.sortItems(0, Qt.SortOrder.AscendingOrder)
            expanded = self.vault_pref('expanded', [])
            for path, item in folders.items():
                item.setExpanded(path in expanded)
            self.list.rebuilding = False
            self.rebuild_tabs()
            self.refresh_links()
            self.filter(self.search.text())
            self.setWindowTitle('Vision law — ' + str(vault.root))
            self.restore_board_view()
            self.board.history.activate()
        except Exception as error:
            if new_lease:new_lease.release()
            QMessageBox.warning(self, 'Không mở được vault', str(error))

    def refresh_links(self):
        if not self.vault or not self.boards:
            return
        self.connections = [tuple(edge) for edge in self.boards.get(self.active_board)['edges']
                            if edge[0] in self.board.cards and edge[1] in self.board.cards]
        self.board.redraw_edges()
        self.statusBar().showMessage(f'{len(self.board.cards)} ghi chú trên bảng • {len(self.connections)} đường nối riêng • Bảng tự lưu')

    def save_layout(self):
        if self.vault and self.boards and self.active_board:
            try:
                data = self.boards.get(self.active_board)
                missing = {name:pos for name,pos in data['positions'].items() if name not in self.names}
                data['positions'] = {**missing, **{name:[card.x(),card.y()] for name,card in self.board.cards.items()}}
                # Missing notes remain in the saved board rather than silently disappearing.
                center=self.board.mapToScene(self.board.viewport().rect().center())
                data['view']={'scale':self.board.transform().m11(),'center':[center.x(),center.y()]}
                self.boards.data['active'] = self.active_board
                self.boards.save()
            except Exception as error:
                QMessageBox.warning(self,'Không lưu được bảng',str(error))
                return False
        return True

    def rebuild_tabs(self):
        self.changing_tabs = True
        while self.tabs.count(): self.tabs.removeTab(0)
        for identity in self.boards.data['open']:
            data = self.boards.get(identity)
            index = self.tabs.addTab(data['name'])
            self.tabs.setTabData(index,identity)
        identities = self.boards.data['open']
        if self.active_board in identities: self.tabs.setCurrentIndex(identities.index(self.active_board))
        self.changing_tabs = False

    def show_board(self,identity):
        self.board.history.tim.stop();self.board.history.commit()
        if not self.close_documents(): return
        self.layout_timer.stop()
        self.board.cancel_connection()
        self.board.cancel_edge_click()
        if self.board.edge_editor: self.board.edge_editor.close()
        self.active_board = identity
        self.boards.data['active'] = identity
        self.board.show_palette(None)
        self.board.cards, self.board.edges = {}, []
        self.board.scene().clear()
        for name,position in self.boards.get(identity)['positions'].items():
            if name not in self.names: continue
            card = Card(self.board,name,position)
            self.board.cards[name] = card
            self.board.scene().addItem(card)
        self.refresh_links()
        self.restore_board_view()
        self.boards.save()
        self.board.history.activate()

    def switch_tab(self,index):
        if self.changing_tabs or index<0 or not self.boards: return
        identity = self.tabs.tabData(index)
        if identity != self.active_board:
            if not self.close_documents():
                self.rebuild_tabs();return
            if not self.save_layout():
                self.rebuild_tabs()
                return
            self.show_board(identity)

    def tabs_reordered(self,*_):
        if self.changing_tabs or not self.boards: return
        self.boards.data['open'] = [self.tabs.tabData(i) for i in range(self.tabs.count())]
        self.boards.save()

    def new_board(self):
        if not self.vault or not self.close_documents(): return
        name,ok=QInputDialog.getText(self,'Bảng mới','Tên bảng:')
        if ok and name.strip() and self.save_layout():
            identity=self.boards.create(name.strip(),self.selected_folder())
            self.show_board(identity)
            self.rebuild_tabs()
            self.reload()

    def open_board_id(self,identity):
        if not self.save_layout() or not self.close_documents():return
        if identity not in self.boards.data['open']:self.boards.data['open'].append(identity)
        self.show_board(identity);self.rebuild_tabs();self.show_board_page()

    def open_board(self):
        if not self.boards or not self.close_documents(): return
        choices=self.boards.data['boards']
        labels=[str(i+1)+'. '+b['name'] for i,b in enumerate(choices)]
        label,ok=QInputDialog.getItem(self,'Mở bảng đã lưu','Bảng:',labels,0,False)
        if ok and self.save_layout():
            identity=choices[labels.index(label)]['id']
            if identity not in self.boards.data['open']: self.boards.data['open'].append(identity)
            self.show_board(identity)
            self.rebuild_tabs()

    def close_tab(self,index):
        if not self.boards or not self.close_documents() or not self.save_layout(): return
        identity=self.tabs.tabData(index)
        self.boards.data['open'].remove(identity)
        if not self.boards.data['open']:
            # Closing never deletes a saved board. Leave a fresh empty board open.
            new_id=self.boards.create('Bảng mới')
        else: new_id=self.boards.data['open'][max(0,index-1)]
        if identity==self.active_board: self.show_board(new_id)
        self.boards.save()
        self.rebuild_tabs()

    def rename_board(self,index):
        if index<0 or not self.boards: return
        data=self.boards.get(self.tabs.tabData(index))
        name,ok=QInputDialog.getText(self,'Đổi tên bảng','Tên:',text=data['name'])
        if ok and name.strip():
            try:
                self.boards.rename(data['id'],name.strip())
                self.reload()
            except Exception as error:QMessageBox.warning(self,'Không đổi tên bảng được',str(error))

    def add_to_board(self,names):
        count=len(self.board.cards)
        for name in names:
            if name not in self.names or name in self.board.cards: continue
            card=Card(self.board,name,[(count%3)*310,(count//3)*180])
            self.board.cards[name]=card
            self.board.scene().addItem(card)
            count+=1
        self.save_layout()
        self.refresh_links()

    def add_notes_dialog(self):
        if not self.vault: return
        dialog=QDialog(self)
        dialog.setWindowTitle('Thêm ghi chú / thư mục vào bảng')
        dialog.resize(560,540)
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Chọn nhiều mục bằng Ctrl / Shift. Thư mục bao gồm các thư mục con.'))
        listing=QListWidget()
        listing.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        options=[('Toàn bộ vault','')]+[(f+' /',f) for f in self.vault.folders()]+[(n,n) for n in self.names]
        for label,value in options:
            listing.addItem(label)
        layout.addWidget(listing)
        button=QPushButton('Thêm vào bảng')
        def accept():
            chosen=[]
            for item in listing.selectedItems():
                value=options[listing.row(item)][1]
                chosen.extend(n for n in self.names if not value or n==value or n.startswith(value+'/'))
            self.add_to_board(chosen)
            dialog.accept()
            self.fit()
        button.clicked.connect(accept)
        layout.addWidget(button)
        dialog.exec()

    def add_connection(self,source,target,source_port=None,target_port=None):
        if not self.save_layout(): return
        try:
            self.boards.connect(self.active_board,source,target)
            if source_port and target_port:
                data=self.boards.get(self.active_board)
                data.setdefault('ports',{})[source+'\n'+target]={'source':source_port,'target':target_port}
                self.boards.save()
            self.refresh_links()
        except Exception as error: QMessageBox.warning(self,'Không lưu được đường nối',str(error))

    def remove_connection(self,pair):
        data=self.boards.get(self.active_board)
        data['edges']=[edge for edge in data['edges'] if tuple(edge)!=tuple(pair)]
        self.boards.save()
        self.refresh_links()

    def remove_from_board(self,name):
        data=self.boards.get(self.active_board)
        data['edges']=[e for e in data['edges'] if name not in e]
        card=self.board.cards.pop(name)
        self.board.scene().removeItem(card)
        self.save_layout()
        self.refresh_links()

    def reload(self, preserve_documents=False):
        if self.vault:
            self.layout_timer.stop()
            self.load(self.vault.root,preserve_documents=preserve_documents,skip_save=True)

    def copy_path(self, path):
        QApplication.clipboard().setText(path)

    def create_in_folder(self, folder):
        name, ok = QInputDialog.getText(self, 'Tạo ghi chú', 'Tên ghi chú:')
        if ok:
            try:
                relative = self.vault.create(name, folder)
                self.reload()
                self.add_to_board([relative])
                item = self.tree_items[relative]
                parent = item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                self.list.setCurrentItem(item)
                self.edit(relative)
            except Exception as error:
                QMessageBox.warning(self, 'Không tạo được', str(error))

    def create(self):
        if not self.vault:
            self.open_vault()
        if not self.vault:
            return
        folder = self.vault_pref('new_folder', '')
        if folder == '@selected':
            folder = self.selected_folder()
        self.create_in_folder(folder)

    def connect_notes(self):
        names=list(self.board.cards)
        if len(names) < 2:
            return
        source, ok = QInputDialog.getItem(self, 'Nối ghi chú', 'Từ ghi chú:', names, 0, False)
        if not ok:
            return
        targets = [n for n in names if n != source]
        target, ok = QInputDialog.getItem(self, 'Nối ghi chú', 'Đến ghi chú:', targets, 0, False)
        if ok:
            try:
                self.add_connection(source, target)
            except Exception as error:
                QMessageBox.warning(self, 'Không nối được', str(error))

    def close_documents(self):
        for document in list(self.documents.values())[::-1]:
            if not document.close(): return False
        return True

    def show_board_page(self):
        self.desk.board()

    def cycle_document(self):
        self.page_switcher.advance()

    def position_document(self,document):
        pass  # The MDI window owns its position and size.

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'desk'):self.desk.resize()

    def raise_document(self, document):
        document.refresh_relations()
        self.desk.open(document)
        for item in self.documents.values():item.refresh_stack()

    def edit(self, name):
        try:
            if name in self.documents:
                self.raise_document(self.documents[name]);return
            from dossier import Dossier
            document=Dossier(self,name)
            self.documents[name]=document
            self.document_order.append(name)
            self.raise_document(document)
        except Exception as error:
            QMessageBox.warning(self, 'Không mở được ghi chú', str(error))

    def focus(self, name):
        if name not in self.board.cards:
            self.add_to_board([name])
        card = self.board.cards[name]
        self.board.centerOn(card)
        self.board.scene().clearSelection()
        card.setSelected(True)
        self.edit(name)

    def filter(self, query):
        self.list.rebuilding = True
        def visit(item):
            if item.childCount():
                visible = [visit(item.child(i)) for i in range(item.childCount())]
                show = any(visible)
                if query and show: item.setExpanded(True)
            else:
                name = item.data(0, Qt.ItemDataRole.UserRole) or (self.boards.relative_path(item.data(0,BOARD)) if item.data(0,BOARD) else item.text(0))
                show = query.casefold() in name.casefold()
            item.setHidden(not show)
            return show
        root = self.list.invisibleRootItem()
        for i in range(root.childCount()):
            visit(root.child(i))
        if not query:
            expanded = self.vault_pref('expanded', [])
            for path, item in getattr(self, 'folder_items', {}).items():
                item.setExpanded(path in expanded)
        self.list.rebuilding = False

    def restore_board_view(self):
        if not self.boards or not self.active_board:return
        view=self.boards.get(self.active_board).get('view')
        if view:
            self.board.resetTransform();scale=max(0.01,min(3.0,float(view['scale'])))
            self.board.scale(scale,scale);self.board.centerOn(QPointF(*view['center']));self.update_zoom_display()
        else:self.fit()

    def update_zoom_display(self):
        if not hasattr(self,'zoom_display'):return
        self.zoom_display.blockSignals(True);self.zoom_display.setValue(self.board.transform().m11()*100);self.zoom_display.blockSignals(False)

    def fit(self):
        if self.board.cards:
            rect = self.board.scene().itemsBoundingRect().adjusted(-70, -70, 70, 70)
            self.board.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            if self.board.transform().m11() > 1:
                self.board.resetTransform()
                self.board.centerOn(rect.center())
            self.update_zoom_display();self.board.history.changed()

    def closeEvent(self, event):
        if self.close_documents() and self.save_layout():
            self.layout_timer.stop()
            self.board.history.tim.stop()
            self.board.cancel_edge_click()
            self.page_switcher.finish(False)
            QApplication.instance().removeEventFilter(self.page_switcher)
            if self._vault_lease:self._vault_lease.release();self._vault_lease=None
            event.accept()
        else:
            event.ignore()

def main():
    from version import VERSION
    if '--version' in sys.argv:
        print('Vision law '+VERSION);return
    app = QApplication([sys.argv[0], '-name', 'vision-law'])
    app.setApplicationName('Vision law');app.setApplicationVersion(VERSION)
    app.setApplicationDisplayName('Vision law');app.setDesktopFileName('vision-law')
    app.setWindowIcon(QIcon(str(Path(__file__).parent/'assets/vision-law.svg')))
    from runtime import configure_logging,default_vault,save_recovery,offer_recovery
    configure_logging();apply_theme(app)
    arguments=[arg for arg in sys.argv[1:] if not arg.startswith('--')]
    root=Path(arguments[0]).expanduser() if arguments else default_vault()
    window=Window(root);app.vision_window=window
    if '--smoke-test' not in sys.argv:offer_recovery(window)
    recovery_timer=QTimer(window);recovery_timer.setInterval(5000)
    recovery_timer.timeout.connect(lambda:save_recovery(window));recovery_timer.start()
    app.aboutToQuit.connect(lambda:save_recovery(window))
    window.show()
    QTimer.singleShot(0,lambda:(window.restore_board_view(),window.board.history.activate()))
    if '--smoke-test' in sys.argv:
        def smoke():
            try:
                if not window.vault or not window.boards:raise RuntimeError('Vault did not load')
                name=window.vault.create('Kiểm tra đóng gói')
                window.reload();window.add_to_board([name]);window.edit(name)
                document=window.documents[name];document.input.setPlainText('Nội dung kiểm tra\n\nDòng thứ ba')
                if not document.save():raise RuntimeError('Note save failed')
                print('SMOKE_OK '+VERSION,flush=True)
                window.close();app.quit()
            except Exception:
                import traceback;traceback.print_exc();app.exit(2)
        QTimer.singleShot(150,smoke)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
