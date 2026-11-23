"""One independent .vlaw file per board; session state is stored separately."""
import json
import uuid
import math
from pathlib import Path
from storage import atomic_write,fingerprint,ConflictError

class Boards:
    def __init__(self,vault):
        self.vault=vault;self._reference_signature=None;self._files={};self._revisions={}
        self.path=vault.root/'.vision-law'/'boards.json'  # legacy, retained as a backup
        self.session_path=vault.root/'.vision-law'/'board-files.json'
        if self.session_path.exists():
            self.data=json.loads(self.session_path.read_text(encoding='utf-8'))
            self.data['boards']=[]
            for path in self.files():
                text=path.read_text(encoding='utf-8');document=json.loads(text)
                if document.get('format')!='vision-law-board' or document.get('version')!=1:raise ValueError('Tệp bảng không được hỗ trợ: '+str(path))
                board=document.get('board',{})
                self.validate(board)
                if board['id'] in self._files:raise ValueError('Hai tệp bảng trùng định danh; hãy dùng Nhân bản bảng thay vì sao chép tệp trong cùng vault.')
                board['name']=path.stem
                self._files[board['id']]=str(path.relative_to(vault.root));self._revisions[board['id']]=fingerprint(text)
                self.data['boards'].append(board)
            if not self.data['boards']:
                board=self.make('Bảng mới');self.data['boards']=[board]
        else:
            if self.path.exists():
                text=self.path.read_text(encoding='utf-8');self.data=json.loads(text)
                if self.data.get('version')!=1 or not self.data.get('boards'):raise ValueError('Dữ liệu bảng cũ không hợp lệ')
                backup=self.path.with_name('boards-before-independent-files.json')
                if not backup.exists():atomic_write(backup,text)
                for board in self.data['boards']:self.validate(board)
            else:
                positions=vault.layout()
                for i,name in enumerate(vault.notes()):positions.setdefault(name,[(i%3)*310,(i//3)*180])
                board=self.make('Bảng kiến thức',positions)
                self.data={'version':1,'boards':[] if self.files() else [board],'open':[] if self.files() else [board['id']],'active':None if self.files() else board['id']}
            # Existing independent files can also be opened in a fresh vault.
            for path in self.files():
                text=path.read_text(encoding='utf-8');doc=json.loads(text);board=doc.get('board',{})
                if doc.get('format')!='vision-law-board' or doc.get('version')!=1:raise ValueError('Tệp bảng không hợp lệ: '+str(path))
                self.validate(board)
                existing=next((b for b in self.data['boards'] if b['id']==board['id']),None)
                board['name']=path.stem
                if existing is not None:existing.clear();existing.update(board)
                else:self.data['boards'].append(board)
                self._files[board['id']]=str(path.relative_to(vault.root));self._revisions[board['id']]=fingerprint(text)
        if self.data.get('tier_palette',1)<3:
            from card_visuals import COLORS,OLD_TIER_COLORS,PREVIOUS_TIER_COLORS
            previous=OLD_TIER_COLORS if self.data.get('tier_palette',1)<2 else PREVIOUS_TIER_COLORS
            for board in self.data['boards']:
                for style in board.get('styles',{}).values():
                    tier=max(1,min(10,int(style.get('tier',1))))
                    if not style.get('custom_color') and style.get('color')==previous[tier-1]:style['color']=COLORS[tier-1]
            self.data['tier_palette']=3
        identities={b['id'] for b in self.data['boards']}
        self.data['open']=[i for i in self.data.get('open',[]) if i in identities]
        if self.data.get('active') not in identities:self.data['active']=self.data['boards'][0]['id']
        if self.data['active'] not in self.data['open']:self.data['open'].append(self.data['active'])
        self.save()

    def files(self):
        return sorted(p for p in self.vault.root.rglob('*.vlaw') if p.is_file() and p.resolve().is_relative_to(self.vault.root) and not any(part.startswith('.') for part in p.relative_to(self.vault.root).parts))
    @staticmethod
    def validate(board):
        def fail():raise ValueError('Dữ liệu bảng không hợp lệ; chưa ghi đè tệp.')
        def path(value):
            if not isinstance(value,str) or not value or '\\' in value or any(ord(c)<32 for c in value):fail()
            p=Path(value)
            if p.is_absolute() or '..' in p.parts or any(part.startswith('.') for part in p.parts) or p.suffix.lower()!='.md':fail()
        def point(value):
            if not isinstance(value,list) or len(value)!=2 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in value):fail()
        if not isinstance(board,dict) or not all(k in board for k in ('id','name','positions','edges')):fail()
        if not isinstance(board['id'],str) or not board['id'] or not isinstance(board['name'],str):fail()
        if not isinstance(board['positions'],dict) or not isinstance(board['edges'],list):fail()
        for name,position in board['positions'].items():path(name);point(position)
        for edge in board['edges']:
            if not isinstance(edge,(list,tuple)) or len(edge)!=2:fail()
            for name in edge:path(name)
        for field in ('styles','dossiers'):
            if not isinstance(board.get(field,{}),dict):fail()
            for name in board.get(field,{}):path(name)
        for style in board.get('styles',{}).values():
            if not isinstance(style,dict) or not isinstance(style.get('tier',1),int) or not 1<=style.get('tier',1)<=10:fail()
        for field in ('ports','edge_styles','edge_categories'):
            if not isinstance(board.get(field,{}),dict):fail()
            for key,value in board.get(field,{}).items():
                if not isinstance(key,str) or len(key.split('\n'))!=2:fail()
                for name in key.split('\n'):path(name)
                if field=='edge_categories' and (not isinstance(value,list) or not all(isinstance(c,str) for c in value)):fail()
                if field in ('ports','edge_styles') and not isinstance(value,dict):fail()
                if field=='ports' and any(port not in ('left','right','top','bottom') for port in value.values()):fail()
        if 'view' in board:
            view=board['view']
            if not isinstance(view,dict) or not isinstance(view.get('scale'),(int,float)) or not math.isfinite(view['scale']) or view['scale']<=0:fail()
            point(view.get('center'))
        if not isinstance(board.get('relation_categories',[]),list):fail()
        for category in board.get('relation_categories',[]):
            if not isinstance(category,dict) or not isinstance(category.get('id'),str) or not isinstance(category.get('name'),str):fail()

    @staticmethod
    def make(name,positions=None):return {'id':uuid.uuid4().hex,'name':name,'positions':positions or {},'edges':[]}
    def get(self,identity):return next(b for b in self.data['boards'] if b['id']==identity)
    def relative_path(self,identity):return self._files[identity]
    def allocate(self,name,folder=''):
        name=name.strip().removesuffix('.vlaw')
        self.vault.validate_name(name);parent=self.vault.folder_path(folder)
        candidate=parent/(name+'.vlaw');i=2
        reserved=set(self._files.values())
        while candidate.exists() or str(candidate.relative_to(self.vault.root)) in reserved:
            candidate=parent/(name+' ('+str(i)+').vlaw');i+=1
        return str(candidate.relative_to(self.vault.root))
    def create(self,name,folder=''):
        board=self.make(name);self._files[board['id']]=self.allocate(name,folder)
        board['name']=Path(self._files[board['id']]).stem
        self.data['boards'].append(board);self.data['open'].append(board['id']);self.data['active']=board['id'];self.save();return board['id']
    def duplicate(self,identity,name,folder=''):
        from copy import deepcopy
        board=deepcopy(self.get(identity));board['id']=uuid.uuid4().hex
        self._files[board['id']]=self.allocate(name,folder);board['name']=Path(self._files[board['id']]).stem
        self.data['boards'].append(board);self.data['open'].append(board['id']);self.data['active']=board['id'];self.save();return board['id']

    def rename(self,identity,name):
        name=name.strip().removesuffix('.vlaw')
        self.vault.validate_name(name);old=self.vault.root/self._files[identity];new=old.with_name(name.strip()+'.vlaw')
        if new==old:return
        if new.exists():raise FileExistsError('Tệp bảng đã tồn tại')
        if fingerprint(old.read_text(encoding='utf-8'))!=self._revisions[identity]:raise ConflictError('Tệp bảng đã thay đổi bên ngoài; hãy tải lại.')
        old.rename(new);self._files[identity]=str(new.relative_to(self.vault.root));self.get(identity)['name']=new.stem;self.save()
    def sync_references(self):
        from portable_refs import sync
        relevant=[{k:v for k,v in b.items() if k in ('id','name','edges','edge_categories','relation_categories','edge_styles','dossiers')} for b in self.data['boards']]
        signature=json.dumps(relevant,ensure_ascii=False,sort_keys=True)
        if signature!=self._reference_signature:sync(self.vault,self.data);self._reference_signature=signature
    def save(self):
        planned=[]
        for board in self.data['boards']:
            self.validate(board)
            identity=board['id']
            if identity not in self._files:
                self._files[identity]=self.allocate(board['name']);board['name']=Path(self._files[identity]).stem
            path=self.vault.root/self._files[identity]
            text=json.dumps({'format':'vision-law-board','version':1,'board':board},ensure_ascii=False,indent=2)
            if path.exists():
                current=path.read_text(encoding='utf-8')
                if identity not in self._revisions or fingerprint(current)!=self._revisions[identity]:raise ConflictError('Tệp bảng đã thay đổi bên ngoài: '+str(path)+'; hãy tải lại trước khi lưu.')
            elif identity in self._revisions:raise ConflictError('Tệp bảng đã bị di chuyển/xóa bên ngoài; hãy tải lại.')
            else:current=None
            planned.append((identity,path,current,text))
        for identity,path,current,text in planned:
            if current!=text:
                if current is not None:atomic_write(self.vault.root/'.vision-law'/'board-backups'/self._files[identity],current)
                atomic_write(path,text)
            self._revisions[identity]=fingerprint(text)
        session={k:v for k,v in self.data.items() if k!='boards'}
        atomic_write(self.session_path,json.dumps(session,ensure_ascii=False,indent=2))
        self.sync_references()
        observer=getattr(self,'on_change',None)
        if observer:observer()
    def connect(self,identity,source,target):
        board=self.get(identity)
        if source==target or source not in board['positions'] or target not in board['positions']:return
        if [source,target] not in board['edges']:board['edges'].append([source,target]);self.save()
