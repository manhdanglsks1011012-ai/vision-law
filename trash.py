"""Recoverable vault-local deletion. Never purges files."""
from pathlib import Path
from datetime import datetime,timezone
import uuid,json
from storage import atomic_write

def entries(vault):
    path=vault.root/'.trash/index.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
def move(vault,relative):
    if (vault.root/relative).is_symlink():raise ValueError('Không chuyển liên kết tượng trưng vào thùng rác bằng thao tác này.')
    source=vault.folder_path(relative)
    if source==vault.root or not source.exists():raise ValueError('Không thể xóa mục này')
    identity=uuid.uuid4().hex;target=vault.root/'.trash'/identity/source.name
    items=entries(vault)
    item={'id':identity,'original':relative,'stored':str(target.relative_to(vault.root)),'time':datetime.now(timezone.utc).isoformat()}
    target.parent.mkdir(parents=True,exist_ok=False)
    source.rename(target)
    try:atomic_write(vault.root/'.trash/index.json',json.dumps(items+[item],ensure_ascii=False,indent=2))
    except Exception:target.rename(source);raise
    return identity

def restore(vault,identity):
    items=entries(vault);item=next(i for i in items if i['id']==identity)
    source=(vault.root/item['stored']).resolve();target=vault.folder_path(item['original'])
    if not source.is_relative_to((vault.root/'.trash').resolve()):raise ValueError('Đường dẫn thùng rác không hợp lệ')
    if target.exists():raise FileExistsError('Đường dẫn gốc đã tồn tại. Hãy đổi tên mục hiện có trước khi khôi phục.')
    target.parent.mkdir(parents=True,exist_ok=True);source.rename(target)
    try:atomic_write(vault.root/'.trash/index.json',json.dumps([i for i in items if i['id']!=identity],ensure_ascii=False,indent=2))
    except Exception:target.rename(source);raise
    return item['original']
