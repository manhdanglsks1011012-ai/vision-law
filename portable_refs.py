"""Append-only portable wikilinks; Markdown body is never rewritten by export."""
import json,re
from pathlib import Path
from storage import atomic_write
START='<!-- vision-law-references:start -->'
END='<!-- vision-law-references:end -->'
BLOCK=re.compile(r'(?:\r?\n){0,2}<!-- vision-law-references:start -->.*?<!-- vision-law-references:end -->(?:\r?\n)?',re.S)
MANIFEST=re.compile(r'<!-- vision-law-references-data: (.*?) -->')
def split_references(text):
    if text.count(START)!=text.count(END) or text.count(START)>1:
        raise ValueError('Phần dẫn chiếu dự phòng không đầy đủ; chưa ghi đè tệp để tránh mất dữ liệu.')
    match=BLOCK.search(text)
    if not match:return text,''
    return text[:match.start()]+text[match.end():],match[0]
def strip_references(text):return split_references(text)[0]
def read_manifest(text):
    match=MANIFEST.search(text)
    if not match:return {}
    try:return json.loads(match[1])
    except (ValueError,TypeError):raise ValueError('Phần dẫn chiếu Vision law bị lỗi; giữ nguyên tệp để phục hồi.')
def clean(value):return ' '.join(str(value).split()).replace('<!--','&lt;!--').replace('-->','--&gt;')
def render(core,entries,existing=None):
    lines=[START,'## Dẫn chiếu','']
    for target,contexts in sorted(entries.items()):
        title=Path(target).stem
        link='[['+target.removesuffix('.md')+']]' if target not in (existing or set()) else '**'+title+'**'
        lines.append('- '+link)
        for context in contexts.values():
            categories=' · '.join(context.get('categories',[])) or 'Chưa phân loại'
            lines.append('  - Danh mục: '+clean(categories)+' | Bảng: '+clean(context['name']))
            if context.get('note'):lines.append('    - Ghi chú: '+clean(context['note']))
    payload=json.dumps(entries,ensure_ascii=False,separators=(',',':')).replace('-->','--\\u003e')
    lines.extend(['','<!-- vision-law-references-data: '+payload+' -->',END])
    return core+'\n\n'+'\n'.join(lines)+'\n'
def sync(vault,data):
    from relation_types import ensure_categories
    contributions={}
    for board in data['boards']:
        ensure_categories(board)
        pairs={tuple(p) for p in board['edges']}
        pairs.update(tuple(key.split('\n')) for key in board.get('edge_categories',{}))
        pairs.update(tuple(key.split('\n')) for key in board.get('edge_styles',{}))
        categories={c['id']:c['name'] for c in board['relation_categories']}
        for pair in pairs:
            if len(pair)!=2:continue
            source,target=pair;key='\n'.join(pair)
            if not vault.path(source).exists():continue
            context={'name':board['name'],'categories':[categories[c] for c in board.get('edge_categories',{}).get(key,[]) if c in categories],
                     'note':board.get('edge_styles',{}).get(key,{}).get('label','')}
            contributions.setdefault(source,{ }).setdefault(target,{})[board['id']]=context
    notes=vault.notes();updates=[]
    for source,entries in contributions.items():
        old,revision=vault.read(source);core,_=split_references(old)
        history=read_manifest(old)
        for target,contexts in entries.items():history.setdefault(target,{}).update(contexts)
        existing=set()
        for target in re.findall(r'(?<!!)\[\[([^\]]+)\]\]',core):
            resolved=vault.resolve(target.split('|')[0].split('#')[0],source,notes)
            if resolved:existing.add(resolved)
        updated=render(core,history,existing)
        if old!=updated:updates.append((source,old,revision,updated))
    for source,old,revision,updated in updates:
        backup=vault.root/'.vision-law'/'reference-backups'/source
        if not backup.exists():atomic_write(backup,old)
        vault.save(source,updated,revision)
    return [u[0] for u in updates]

def remap(text,mapping):
    if not MANIFEST.search(text):return text
    entries=read_manifest(text)
    updated={}
    for target,contexts in entries.items():updated.setdefault(mapping(target),{}).update(contexts)
    payload=json.dumps(updated,ensure_ascii=False,separators=(',',':')).replace('-->','--\\u003e')
    return MANIFEST.sub(lambda _: '<!-- vision-law-references-data: '+payload+' -->',text)
