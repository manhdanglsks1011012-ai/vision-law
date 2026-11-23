"""File-backed vault. Markdown is authoritative; layout contains only presentation."""
from pathlib import Path
import hashlib
import json
import os
import re
import tempfile
import stat
import errno

class ConflictError(Exception):
    pass

def fingerprint(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    old_mode=stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        if old_mode is not None:os.fchmod(fd,old_mode)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if hasattr(os,'O_DIRECTORY'):
            try:directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
            except PermissionError:directory=None
            if directory is not None:
                try:os.fsync(directory)
                finally:os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

class Vault:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ValueError('Thư mục không tồn tại')
        for internal in ('.vision-law','.trash'):
            target=self.root/internal
            if target.is_symlink() and not target.resolve().is_relative_to(self.root):raise ValueError('Thư mục dữ liệu nội bộ không được trỏ ra ngoài vault')
        self.layout_path = self.root / '.vision-law' / 'board.json'

    def path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or path.suffix.lower() != '.md':
            raise ValueError('Đường dẫn ghi chú không hợp lệ')
        return path

    def notes(self):
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*.md')
                      if not any(part.startswith('.') for part in p.relative_to(self.root).parts)
                      and p.resolve().is_relative_to(self.root))

    def read(self, relative):
        text = self.path(relative).read_text(encoding='utf-8')
        return text, fingerprint(text)

    def save(self, relative, text, expected):
        current, revision = self.read(relative)
        if revision != expected:
            raise ConflictError('Tệp đã thay đổi bên ngoài. Nội dung bạn đang sửa được giữ trong cửa sổ này. Hãy sao chép trước khi tải lại.')
        if current != text:
            backup = self.root / '.vision-law' / 'backups' / relative
            atomic_write(backup, current)
            atomic_write(self.path(relative), text)
        return fingerprint(text)

    def folders(self):
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')
                      if p.is_dir() and p.resolve().is_relative_to(self.root)
                      and not any(part.startswith('.') for part in p.relative_to(self.root).parts))

    def folder_path(self, relative=''):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or any(part.startswith('.') for part in Path(relative).parts):
            raise ValueError('Thư mục phải nằm trong vault và không bị ẩn')
        return path

    def create_folder(self, name, parent=''):
        self.validate_name(name)
        path = self.folder_path(parent) / name.strip()
        path.mkdir(exist_ok=False)
        return str(path.relative_to(self.root))

    @staticmethod
    def validate_name(name):
        if any(ord(c)<32 for c in name) or not name.strip() or name.strip().startswith('.') or name.strip().endswith('.') or any(c in name for c in '/\\<>:"|?*[]'):
            raise ValueError('Tên không hợp lệ hoặc chứa ký tự đặc biệt.')

    def create(self, name, folder=''):
        name = name.strip()
        if not name or any(c in name for c in '/\\<>:"|?*[]') or name in {'.', '..'} or name.endswith('.'):
            raise ValueError('Tên không hợp lệ. Không dùng dấu phân cách hoặc ký tự đặc biệt.')
        self.validate_name(name)
        directory = self.folder_path(folder)
        if not directory.is_dir():
            raise ValueError('Thư mục ghi chú không tồn tại')
        relative = str((directory / (name + '.md')).relative_to(self.root))
        with self.path(relative).open('x', encoding='utf-8') as stream:
            stream.write('# ' + name + '\n\n')
        return relative

    def layout(self):
        if not self.layout_path.exists():
            return {}
        data = json.loads(self.layout_path.read_text(encoding='utf-8'))
        if data.get('version') != 1 or not isinstance(data.get('positions'), dict):
            raise ValueError('Định dạng bảng không được hỗ trợ')
        return data['positions']

    def save_layout(self, positions):
        atomic_write(self.layout_path, json.dumps({'version': 1, 'positions': positions}, ensure_ascii=False, indent=2))

    def links(self, relative):
        text, _ = self.read(relative)
        return [m.split('|', 1)[0].split('#', 1)[0].strip() for m in re.findall(r'(?<!!)\[\[([^\]]+)\]\]', text)]

    def resolve(self, target, source, notes):
        target = target.removesuffix('.md')
        candidates = [target + '.md', str(Path(source).parent / (target + '.md'))]
        for candidate in candidates:
            if candidate in notes:
                return candidate
        matches = [n for n in notes if Path(n).stem == target]
        return matches[0] if len(matches) == 1 else None

    def connect(self, source, target):
        text, rev = self.read(source)
        destination = target.removesuffix('.md')
        if any(self.resolve(link, source, self.notes()) == target for link in self.links(source)):
            return
        self.save(source, text.rstrip() + '\n\n[[' + destination + ']]\n', rev)

    def relocate(self, relative, destination):
        """Move a note/folder and preserve resolved wikilinks and board positions."""
        source = self.folder_path(relative)
        dest = self.folder_path(destination)
        if source == self.root or not source.exists() or source.is_symlink():
            raise ValueError('Không thể di chuyển mục này')
        if dest == source:
            return
        if dest.exists() or not dest.parent.is_dir():
            raise ValueError('Đích đã tồn tại hoặc thư mục cha không tồn tại')
        if dest.is_relative_to(source):
            raise ValueError('Không thể đặt thư mục vào bên trong chính nó')
        notes = self.notes()
        def mapped(name):
            path = self.root / name
            return str((dest / path.relative_to(source)).relative_to(self.root)) if path.is_relative_to(source) else name
        originals = {n: self.read(n) for n in notes}
        changes = {}
        for name, (text, revision) in originals.items():
            def replace(match):
                inner = match[1]
                target_alias = inner.split('|', 1)
                target_heading = target_alias[0].split('#', 1)
                target = self.resolve(target_heading[0], name, notes)
                if target is None:
                    return match[0]
                if mapped(target) == target and mapped(name) == name:
                    return match[0]
                new_target = mapped(target).removesuffix('.md')
                if len(target_heading) > 1: new_target += '#' + target_heading[1]
                if len(target_alias) > 1: new_target += '|' + target_alias[1]
                return '[[' + new_target + ']]'
            updated = re.sub(r'\[\[([^\]]+)\]\]', replace, text)
            from portable_refs import remap
            updated=remap(updated,mapped)
            if updated != text:
                changes[name] = updated
        positions = self.layout()
        def rewrite_board(board):
            board['positions'] = {mapped(n): position for n,position in board['positions'].items()}
            board['edges'] = [[mapped(a),mapped(b)] for a,b in board['edges']]
            board['dossiers'] = {mapped(n):{side:[{**g,'members':[mapped(member) for member in g.get('members',[])]} for g in groups] for side,groups in config.items()} for n,config in board.get('dossiers',{}).items()}
            board['styles'] = {mapped(n):style for n,style in board.get('styles',{}).items()}
            board['edge_categories'] = {'\n'.join(mapped(n) for n in key.split('\n')):values for key,values in board.get('edge_categories',{}).items()}
            board['hidden_references'] = ['\n'.join(mapped(n) for n in key.split('\n')) for key in board.get('hidden_references',[])]
            board['edge_styles'] = {'\n'.join(mapped(n) for n in key.split('\n')):style for key,style in board.get('edge_styles',{}).items()}
            board['ports'] = {'\n'.join(mapped(n) for n in key.split('\n')):ports for key,ports in board.get('ports',{}).items()}
        boards_path = self.root / '.vision-law' / 'boards.json'
        boards_original = boards_path.read_text(encoding='utf-8') if boards_path.exists() else None
        boards_updated = None
        if boards_original:
            board_data = json.loads(boards_original)
            for board in board_data['boards']:rewrite_board(board)
            boards_updated = json.dumps(board_data,ensure_ascii=False,indent=2)
        board_files=[]
        for file in self.root.rglob('*.vlaw'):
            if not file.resolve().is_relative_to(self.root) or any(part.startswith('.') for part in file.relative_to(self.root).parts):continue
            original=file.read_text(encoding='utf-8');payload=json.loads(original)
            if payload.get('format')!='vision-law-board':raise ValueError('Tệp bảng không hợp lệ: '+str(file))
            rewrite_board(payload['board'])
            relative=str(file.relative_to(self.root));new_relative=mapped(relative)
            payload['board']['name']=Path(new_relative).stem
            board_files.append((relative,new_relative,original,json.dumps(payload,ensure_ascii=False,indent=2)))
        for name, (_, revision) in originals.items():
            if self.read(name)[1] != revision:
                raise ConflictError('Vault đã thay đổi. Hãy tải lại trước khi di chuyển.')
        for name in changes:
            atomic_write(self.root / '.vision-law/backups' / name, originals[name][0])
        for relative,new_relative,original,updated in board_files:
            if original!=updated:atomic_write(self.root/'.vision-law'/'board-backups'/relative,original)
        source.rename(dest)
        written = []
        try:
            for name, text in changes.items():
                atomic_write(self.path(mapped(name)), text)
                written.append(name)
            for old_relative,new_relative,original,updated in board_files:
                if original!=updated:atomic_write(self.root/new_relative,updated)
            if boards_updated:
                atomic_write(boards_path,boards_updated)
            self.save_layout({mapped(n): pos for n, pos in positions.items()})
        except Exception:
            for old_relative,new_relative,original,updated in board_files:
                if (self.root/new_relative).exists():atomic_write(self.root/new_relative,original)
            if boards_original:
                atomic_write(boards_path, boards_original)
            for name in written:
                atomic_write(self.path(mapped(name)), originals[name][0])
            dest.rename(source)
            raise
