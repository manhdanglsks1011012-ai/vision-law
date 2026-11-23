"""Three-column note dossiers backed by the current board's relationships."""
import uuid
from pathlib import Path
from PyQt6.QtCore import Qt,QTimer
from PyQt6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,
 QLineEdit,QListWidget,QScrollArea,QSplitter,QFrame,QInputDialog,QMessageBox,QMenu,QSizePolicy)
from app import Editor
from card_visuals import details
from relation_types import ensure_categories,merged_relations


def related(window,note,side,all_boards=False):
    records=[]
    boards=window.boards.data['boards'] if all_boards else [window.boards.get(window.active_board)]
    for board in boards:
        for source,target in board['edges']:
            if (side=='out' and source==note) or (side=='in' and target==note):
                other=target if side=='out' else source
                style=board.get('edge_styles',{}).get(source+'\n'+target,{})
                records.append({'other':other,'pair':(source,target),'label':style.get('label',''),
                                'board':board['name'],'board_id':board['id'],'legacy':False})
    return records


def legacy_related(window,note,side):
    result=[]
    for source in ([note] if side=='out' else window.names):
        try:
            import re
            from portable_refs import strip_references
            core=strip_references(window.vault.read(source)[0])
            links=[m.split('|',1)[0].split('#',1)[0] for m in re.findall(r'(?<!!)\[\[([^\]]+)\]\]',core)]
        except OSError: continue
        for link in links:
            target=window.vault.resolve(link,source,window.names)
            if target and (side=='out' or target==note):
                other=target if side=='out' else source
                if other!=note and not any(r['other']==other for r in result):
                    result.append({'other':other,'pair':(source,target),'label':'Dẫn chiếu trong tệp Markdown',
                                   'board':'Markdown','board_id':None,'legacy':True})
    return result

class LinkEntry(QWidget):
    def __init__(self,dossier,side,group_id):
        super().__init__();self.dossier=dossier;self.side=side;self.group_id=group_id
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.input=QLineEdit();self.input.setPlaceholderText('Gõ [[ để thêm liên kết…')
        self.scope=QComboBox();self.scope.addItems(['Toàn vault','Cùng thư mục','Cùng nhánh thư mục'])
        self.scope.setToolTip('Đổi phạm vi ngay khi nhập liên kết')
        self.results=QListWidget();self.results.setMaximumHeight(150)
        layout.addWidget(self.input);layout.addWidget(self.scope);layout.addWidget(self.results)
        self.scope.hide();self.results.hide()
        self.input.textChanged.connect(self.suggest);self.scope.currentIndexChanged.connect(self.suggest)
        self.input.returnPressed.connect(self.choose)
        self.results.itemActivated.connect(lambda _:self.choose())
        self.results.itemClicked.connect(lambda _:self.choose())
        self.input.installEventFilter(self)
        self.candidates=[]

    def eventFilter(self,obj,event):
        from PyQt6.QtCore import QEvent
        if obj is self.input and event.type()==QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Down,Qt.Key.Key_Up):
                step=1 if event.key()==Qt.Key.Key_Down else -1
                self.results.setCurrentRow(max(0,min(self.results.count()-1,self.results.currentRow()+step)));return True
            if event.key()==Qt.Key.Key_Escape:
                self.input.clear();return True
        return super().eventFilter(obj,event)

    def suggest(self,*_):
        text=self.input.text();active='[[' in text
        self.scope.setVisible(active);self.results.setVisible(active)
        if not active:return
        query=text.rsplit('[[',1)[-1].removesuffix(']]').strip().casefold()
        folder=Path(self.dossier.name).parent
        self.candidates=[];self.results.clear()
        for name in self.dossier.window.names:
            if name==self.dossier.name:continue
            parent=Path(name).parent
            if self.scope.currentIndex()==1 and parent!=folder:continue
            if self.scope.currentIndex()==2 and not Path(name).is_relative_to(folder):continue
            title,_=details(self.dossier.window.vault.read(name)[0],name)
            if query in (title+' '+name).casefold():
                self.candidates.append(name);self.results.addItem(title+'\n'+name)
        self.results.addItem('＋ Tạo ghi chú mới…');self.results.setCurrentRow(0)

    def choose(self):
        row=self.results.currentRow()
        if row<0 or not self.results.isVisible():return
        if row>=len(self.candidates):
            text=self.input.text().rsplit('[[',1)[-1].removesuffix(']]').strip()
            name,ok=QInputDialog.getText(self,'Tạo ghi chú','Tên:',text=text)
            if not ok:return
            folders=['']+self.dossier.window.vault.folders()
            label,ok=QInputDialog.getItem(self,'Nơi lưu','Thư mục:', ['Gốc vault']+folders[1:],0,False)
            if not ok:return
            folder=folders[(['Gốc vault']+folders[1:]).index(label)]
            try:
                other=self.dossier.window.vault.create(name,folder)
                self.dossier.window.reload(preserve_documents=True)
            except Exception as error:
                QMessageBox.warning(self,'Không tạo được',str(error));return
        else:other=self.candidates[row]
        self.dossier.add_relation(self.side,self.group_id,other)

class Dossier(Editor):
    def __init__(self,window,name):
        super().__init__(window,name)
        self.setWindowFlags(Qt.WindowType.Widget)
        from PyQt6.QtGui import QShortcut,QKeySequence
        for button in self.findChildren(QPushButton):
            if button.shortcut().toString()=='Ctrl+S':button.setShortcut(QKeySequence())
        self.save_shortcut=QShortcut(QKeySequence('Ctrl+S'),self)
        self.save_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.save_shortcut.activated.connect(self.save)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("documentSheet")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
        self.board_id=window.active_board
        self.resize(1370,820)
        self.setWindowTitle('Lược đồ · '+Path(name).stem+' — Vision law')
        self.expanded_groups=set();self.collapsed_groups=set()
        self.relationship_cards=[]
        outer=self.layout()
        # Keep the tested inputs and save commands, replace only their presentation.
        while outer.count():
            item=outer.takeAt(0)
            if item.widget():item.widget().hide()
            elif item.layout():
                for j in range(item.layout().count()):
                    widget=item.layout().itemAt(j).widget()
                    if widget:widget.hide()
        outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        self.center=QWidget();self.center.setObjectName('writingPage')
        center_layout=QVBoxLayout(self.center);center_layout.setContentsMargins(28,18,28,6);center_layout.setSpacing(6)
        self.title_field.setObjectName('inlineNoteTitle')
        self.title_field.setPlaceholderText('Tiêu đề ghi chú')
        self.title_field.setToolTip('Tiêu đề ghi chú')
        self.summary_field.setObjectName('inlineNoteSummary')
        self.summary_field.setPlaceholderText('Thêm một câu mô tả ngắn…')
        import re
        first=re.match(r'^# +([^\n]+)\n(?:\n)?',self.input.toPlainText())
        self.body_heading_prefix=''
        if first and first[1].strip() in (self.card_title,Path(name).stem):
            self.body_heading_prefix=first[0]
            body=self.input.toPlainText()[first.end():]
            self.input.blockSignals(True);self.input.setPlainText(body);self.input.blockSignals(False)
            self.saved_source=body
        self.title_field.show();self.summary_field.show();self.panes.show()
        center_layout.addWidget(self.title_field)
        center_layout.addWidget(self.summary_field)
        self.input.setObjectName('noteBody');self.preview.setObjectName('noteBody')
        self.input.setStyleSheet('border: none; background: transparent; padding: 12px 0; font-size: '+str(window.prefs.get('editor_size',15))+'px;')
        self.preview.setStyleSheet(self.input.styleSheet())
        center_layout.addWidget(self.panes,1)
        self.message.setText('Đã lưu');self.message.setObjectName('saveState');self.message.show()
        center_layout.addWidget(self.message)
        toolbar=QHBoxLayout();toolbar.setContentsMargins(10,3,10,3)
        self.stack_button=QPushButton('Tài liệu');self.stack_button.clicked.connect(self.stack_menu);self.stack_button.hide()
        self.scope=QComboBox();self.scope.addItems(['Bảng hiện tại','Tất cả bảng'])
        self.scope.setFixedWidth(125);self.scope.setToolTip('Phạm vi liên hệ')
        self.scope.currentIndexChanged.connect(self.refresh_relations)
        toolbar.addWidget(self.scope)
        self.search_relations=QLineEdit();self.search_relations.setPlaceholderText('Lọc liên hệ…')
        self.search_relations.textChanged.connect(self.refresh_relations);self.search_relations.hide()
        toolbar.addWidget(self.search_relations,1)
        toolbar.addStretch()
        left_toggle=QPushButton('◧');left_toggle.setToolTip('Ẩn/hiện liên hệ bên trái')
        left_toggle.clicked.connect(lambda:self.panels['out'][0].setVisible(not self.panels['out'][0].isVisible()))
        toolbar.addWidget(left_toggle)
        right_toggle=QPushButton('◨');right_toggle.setToolTip('Ẩn/hiện liên hệ bên phải')
        right_toggle.clicked.connect(lambda:self.panels['in'][0].setVisible(not self.panels['in'][0].isVisible()))
        toolbar.addWidget(right_toggle)
        options=QPushButton('⋯');options.setToolTip('Định dạng, đọc và quản lý nhóm');options.clicked.connect(self.note_menu);toolbar.addWidget(options)
        outer.addLayout(toolbar)
        self.split=QSplitter();self.panels={}
        for side in ('out','in'):
            scroll=QScrollArea();scroll.setObjectName('relationsPanel');scroll.setWidgetResizable(True);scroll.setMinimumWidth(190)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            content=QWidget();scroll.setWidget(content);self.panels[side]=(scroll,content)
        self.split.addWidget(self.panels['out'][0]);self.split.addWidget(self.center);self.split.addWidget(self.panels['in'][0])
        self.split.setStretchFactor(0,0);self.split.setStretchFactor(1,1);self.split.setStretchFactor(2,0)
        self.split.setSizes([230,900,230]);outer.addWidget(self.split,1)
        self.dossier_chrome=[self.scope,self.search_relations,left_toggle,right_toggle,options]
        self.previous_source=self.input.toPlainText()
        self.input.textChanged.connect(self.guard_links)
        self.refresh_relations()
        self.refresh_stack()

    def note_menu(self):
        menu=QMenu(self)
        read=menu.addAction('Chế độ đọc');read.setCheckable(True);read.setChecked(self.source_toggle.isChecked())
        read.triggered.connect(self.source_toggle.setChecked)
        menu.addAction('Lưu · Ctrl+S',self.save)
        formatting=menu.addMenu('Định dạng')
        for label,marker in [('Đậm · Ctrl+B','**'),('Nghiêng · Ctrl+I','*'),('Gạch chân','<u>'),('Gạch bỏ','~~'),('Tô sáng','=='),('Mã','`')]:
            formatting.addAction(label,lambda checked=False,m=marker:self.input.wrap(m))
        for level in range(1,7):formatting.addAction('Tiêu đề '+str(level),lambda checked=False,n=level:self.input.heading(n))
        menu.addSeparator()
        menu.addAction('Lọc liên hệ…',lambda:(self.search_relations.show(),self.search_relations.setFocus()))
        menu.addAction('Mẫu nhóm…',self.templates)
        menu.addAction('Chọn tài liệu đang mở…',self.stack_menu)
        menu.exec(self.cursor().pos())

    def set_content_only(self,enabled):
        for side in self.panels:self.panels[side][0].setVisible(not enabled)
        for widget in self.dossier_chrome:
            if widget is not self.search_relations:widget.setVisible(not enabled)
        if enabled:self.search_relations.hide()
        self.title_field.show();self.summary_field.show();self.panes.show()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def changed(self):
        dirty=self.input.toPlainText()!=self.saved_source or self.title_field.text()!=self.card_title or self.summary_field.text()!=self.card_summary
        if dirty:super().changed()
        if hasattr(self,'message'):self.message.setText('Chưa lưu' if dirty else 'Đã lưu')

    def guard_links(self):
        text=self.input.toPlainText()
        if text.count('[[')>self.previous_source.count('[['):
            position=self.input.textCursor().position()
            self.input.blockSignals(True)
            self.input.setPlainText(self.previous_source)
            self.input.document().setModified(True)
            cursor=self.input.textCursor();cursor.setPosition(min(position,len(self.previous_source)));self.input.setTextCursor(cursor)
            self.input.blockSignals(False)
            self.render()
            self.message.setText('Tạo liên kết bằng [[ ở các ô hai bên; phần giữa dành cho nội dung.')
            return
        self.previous_source=text

    def save(self):
        result=super().save()
        if result:
            self.previous_source=self.input.toPlainText()
            if hasattr(self,'panels'):self.refresh_all()
            self.message.setText('Đã lưu')
        return result

    def refresh_stack(self):
        self.stack_button.setText('Chồng tài liệu · '+str(len(getattr(self.window,'documents',{})))+' đang mở')

    def stack_menu(self):
        menu=QMenu(self)
        menu.addAction('Bảng chính',self.window.show_board_page)
        for name,document in self.window.documents.items():
            menu.addAction(Path(name).stem,lambda checked=False,d=document:self.window.raise_document(d))
        menu.exec(self.stack_button.mapToGlobal(self.stack_button.rect().bottomLeft()))

    def config(self,side):
        board=self.window.boards.get(self.board_id);ensure_categories(board)
        return board['relation_categories']

    def save_groups(self):
        self.window.boards.save()
        self.window.board.redraw_edges()

    def add_group(self,side):
        name,ok=QInputDialog.getText(self,'Thêm danh mục','Tên loại quan hệ:')
        if ok and name.strip():
            if any(c['name'].casefold()==name.strip().casefold() for c in self.config(side)):
                QMessageBox.information(self,'Danh mục đã có','Tên danh mục này đã tồn tại.');return
            self.config(side).append({'id':uuid.uuid4().hex,'name':name.strip(),'color':'#ad8aff'})
            self.save_groups();self.refresh_all()

    def group_menu(self,side,group):
        menu=QMenu(self)
        def rename():
            name,ok=QInputDialog.getText(self,'Đổi tên danh mục','Tên:',text=group['name'])
            if ok and name.strip():
                if any(c is not group and c['name'].casefold()==name.strip().casefold() for c in self.config(side)):return
                group['name']=name.strip();self.save_groups();self.refresh_all()
        def move(step):
            groups=self.config(side);index=groups.index(group);new=max(0,min(len(groups)-1,index+step))
            groups.insert(new,groups.pop(index));self.save_groups();self.refresh_all()
        def delete():
            board=self.window.boards.get(self.board_id)
            self.config(side).remove(group)
            for key,values in board.get('edge_categories',{}).items():board['edge_categories'][key]=[v for v in values if v!=group['id']]
            self.save_groups();self.refresh_all()
        def color():
            from PyQt6.QtWidgets import QColorDialog
            from PyQt6.QtGui import QColor
            value=QColorDialog.getColor(QColor(group.get('color','#ad8aff')),self)
            if value.isValid():group['color']=value.name();self.save_groups();self.refresh_all()
        menu.addAction('Đổi tên',rename);menu.addAction('Màu danh mục',color)
        menu.addAction('Đưa lên',lambda:move(-1));menu.addAction('Đưa xuống',lambda:move(1))
        menu.addAction('Xóa danh mục (giữ liên kết)',delete)
        menu.exec(self.cursor().pos())

    def templates(self):
        menu=QMenu(self)
        def save():
            name,ok=QInputDialog.getText(self,'Lưu mẫu','Tên mẫu:')
            if ok and name.strip():
                self.window.boards.data.setdefault('dossier_templates',{})[name.strip()]={side:[{k:g[k] for k in ('name','color')} for g in self.config(side)] for side in ('out','in')}
                self.save_groups()
        menu.addAction('Lưu bộ nhóm hiện tại thành mẫu…',save)
        for name,data in self.window.boards.data.get('dossier_templates',{}).items():
            def apply(checked=False,template=data):
                for side,groups in template.items():
                    for group in groups:
                        if not any(g['name']==group['name'] for g in self.config(side)):
                            self.config(side).append({**group,'id':uuid.uuid4().hex})
                self.save_groups();self.refresh_relations()
            menu.addAction('Áp dụng: '+name,apply)
        menu.exec(self.cursor().pos())

    def add_relation(self,side,group_id,other):
        try:
            self.window.add_to_board([self.name,other])
            pair=(self.name,other) if side=='out' else (other,self.name)
            self.window.add_connection(*pair)
            board=self.window.boards.get(self.board_id);ensure_categories(board)
            key='\n'.join(pair)
            if key in board.get('hidden_references',[]):board['hidden_references'].remove(key)
            if group_id:
                chosen=board.setdefault('edge_categories',{}).setdefault(key,[])
                if group_id not in chosen:chosen.append(group_id)
            self.save_groups();self.refresh_all()
        except Exception as error:QMessageBox.warning(self,'Không thêm được liên kết',str(error))

    def refresh_all(self):
        for document in getattr(self.window,'documents',{}).values():document.refresh_relations()
        if self not in getattr(self.window,'documents',{}).values():self.refresh_relations()

    def relation_card(self,record,side):
        other=record['other']
        try:title,summary=details(self.window.vault.read(other)[0],other)
        except OSError:title,summary=Path(other).stem,'Tệp không còn tồn tại'
        row=QWidget();row.setObjectName('referenceRow')
        layout=QHBoxLayout(row);layout.setContentsMargins(3,0,3,0);layout.setSpacing(5)
        bullet=QLabel('·');bullet.setObjectName('muted');layout.addWidget(bullet)
        link=QLabel();link.setObjectName('referenceLink');link.setWordWrap(True)
        from html import escape
        link.setText('<a href="note" style="text-decoration:none;color:#bfa8e9;">'+escape(title)+'</a>')
        link.linkActivated.connect(lambda _:self.window.edit(other))
        tooltip=title+'\n'+other
        if record['label']:tooltip+='\n'+record['label']
        if summary:tooltip+='\n'+summary
        tooltip+='\nBảng: '+record['board']
        link.setToolTip(tooltip);row.setToolTip(tooltip);layout.addWidget(link,1)
        def menu_at(pos):self.relation_menu(record,side)
        for widget in (link,row):
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            widget.customContextMenuRequested.connect(menu_at)
        self.relationship_cards.append(row)
        return row

    def relation_menu(self,record,side):
        menu=QMenu(self)
        menu.addAction('Mở ghi chú',lambda:self.window.edit(record['other']))
        menu.addAction('Sao chép đường dẫn',lambda:self.window.copy_path(record['other']))
        if not self.scope.currentIndex():
            menu.addAction('Phân loại quan hệ…',lambda:self.assign_group(side,record['other']))
            menu.addAction('Lý do liên kết / màu…',lambda:self.edit_relation(record))
            menu.addAction('Đến trên bảng',lambda:self.locate(record['other']))
            def remove():
                board=self.window.boards.get(self.board_id);key='\n'.join(record['pair'])
                if record['pair'] in self.window.connections:self.window.remove_connection(record['pair'])
                hidden=board.setdefault('hidden_references',[])
                if key not in hidden:hidden.append(key)
                self.save_groups();self.refresh_all()
            menu.addAction('Bỏ liên kết khỏi bảng này',remove)
        menu.exec(self.cursor().pos())

    def edit_relation(self,record):
        self.window.board.edit_connection(record['pair'])
        dialog=self.window.board.edge_editor
        dialog.finished.connect(lambda _:self.refresh_all())
        dialog.raise_();dialog.activateWindow()

    def locate(self,other):
        self.window.add_to_board([other]);self.window.board.centerOn(self.window.board.cards[other]);self.window.show_board_page()

    def set_categories(self,pair,category_ids):
        board=self.window.boards.get(self.board_id);ensure_categories(board)
        valid={c['id'] for c in board['relation_categories']}
        board.setdefault('edge_categories',{})['\n'.join(pair)]=[c for c in category_ids if c in valid]
        self.save_groups();self.refresh_all()

    def assign_group(self,side,other):
        board=self.window.boards.get(self.board_id);ensure_categories(board)
        pair=(self.name,other) if side=='out' else (other,self.name)
        key='\n'.join(pair);chosen=board.get('edge_categories',{}).get(key,[])
        menu=QMenu(self)
        for group in self.config(side):
            action=menu.addAction(group['name']);action.setCheckable(True);action.setChecked(group['id'] in chosen)
            def toggle(checked,g=group):
                values=list(board.get('edge_categories',{}).get(key,[]))
                if checked and g['id'] not in values:values.append(g['id'])
                elif not checked and g['id'] in values:values.remove(g['id'])
                self.set_categories(pair,values)
            action.triggered.connect(toggle)
        menu.addSeparator();menu.addAction('Chưa phân loại',lambda:self.set_categories(pair,[]))
        menu.addAction('＋ Thêm danh mục…',lambda:self.add_group(side))
        menu.exec(self.cursor().pos())

    def refresh_relations(self,*_):
        if self.board_id!=self.window.active_board:return
        self.relationship_cards=[]
        for side in ('out','in'):
            old=self.panels[side][1];layout=old.layout()
            if layout is None:layout=QVBoxLayout(old)
            while layout.count():
                item=layout.takeAt(0)
                if item.widget():
                    item.widget().hide()
                    item.widget().deleteLater()
            heading=QLabel('DẪN TỚI →' if side=='out' else '← DẪN VÀO');heading.setObjectName('sectionTitle');layout.addWidget(heading)
            all_boards=bool(self.scope.currentIndex())
            records=merged_relations(self.window,self.name,side,all_boards)
            groups=list(self.config(side))
            if all_boards:
                seen={c['name'] for c in groups}
                for board in self.window.boards.data['boards']:
                    ensure_categories(board)
                    for category in board['relation_categories']:
                        if category['name'] not in seen:groups.append(category);seen.add(category['name'])
            self.build_group(layout,side,{'id':'general','name':'Chưa phân loại','color':'#a29aa9'},[r for r in records if not r['categories']],editable=not all_boards)
            for group in groups:
                selected=[r for r in records if (group['name'] in r['category_names'] if all_boards else group['id'] in r['categories'])]
                self.build_group(layout,side,group,selected,editable=not all_boards)
            if not all_boards:
                button=QPushButton('＋ Thêm danh mục');button.clicked.connect(lambda checked=False,s=side:self.add_group(s));layout.addWidget(button)
            layout.addStretch()
        self.refresh_stack()

    def build_group(self,parent,side,group,records,editable):
        key=side+':'+group['id'];query=self.search_relations.text().casefold()
        records=[r for r in records if query in (r['other']+' '+r['label']).casefold()]
        frame=QFrame();frame.setObjectName('relationGroup')
        layout=QVBoxLayout(frame);layout.setContentsMargins(8,8,8,8)
        collapsed=key in self.collapsed_groups or (not records and group['id']!='general' and key not in self.expanded_groups)
        row=QHBoxLayout();toggle=QPushButton(('▸ ' if collapsed else '▾ ')+group['name'])
        toggle.setMinimumWidth(0);toggle.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        toggle.setToolTip(group['name'])
        toggle.setStyleSheet('text-align:left; font-weight:600; color:'+group.get('color','#ad8aff')+';')
        def collapse():
            if collapsed:
                self.collapsed_groups.discard(key);self.expanded_groups.add(key)
            else:self.collapsed_groups.add(key)
            self.refresh_relations()
        toggle.clicked.connect(collapse);row.addWidget(toggle,1)
        count=QLabel(str(len(records)));count.setObjectName('muted');count.setFixedWidth(20);row.addWidget(count)
        if editable and group['id']!='general':
            more=QPushButton('⋯');more.setStyleSheet('padding:0; font-size:17px;');more.setFixedSize(24,24);more.clicked.connect(lambda:self.group_menu(side,group));row.addWidget(more)
        layout.addLayout(row)
        if not collapsed:
            shown=records if key in self.expanded_groups else records[:3]
            for record in shown:layout.addWidget(self.relation_card(record,side))
            if len(records)>3:
                button=QPushButton('Thu bớt' if key in self.expanded_groups else 'Xem thêm '+str(len(records)-3)+' tài liệu')
                def expand():
                    if key in self.expanded_groups:self.expanded_groups.remove(key)
                    else:self.expanded_groups.add(key)
                    self.refresh_relations()
                button.clicked.connect(expand);layout.addWidget(button)
            if not records:
                label=QLabel('—');label.setToolTip('Chưa có dẫn chiếu trong danh mục này');label.setObjectName('muted');layout.addWidget(label)
            if editable:
                add=QPushButton('＋');add.setObjectName('addReference');add.setToolTip('Thêm dẫn chiếu vào '+group['name'])
                entry=LinkEntry(self,side,None if group['id']=='general' else group['id']);entry.hide()
                def reveal():
                    entry.show();entry.input.setText('[[');entry.input.setFocus();add.hide()
                add.clicked.connect(reveal);layout.addWidget(add);layout.addWidget(entry)
        parent.addWidget(frame)

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape:
            self.close();event.accept();return
        super().keyPressEvent(event)

    def closeEvent(self,event):
        super().closeEvent(event)
        if event.isAccepted():
            self.window.desk.document_closed(self.name)
            for document in self.window.documents.values():document.refresh_stack()
