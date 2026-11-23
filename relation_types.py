"""Semantic categories belong to a directed relation, independent of its origin."""
from copy import deepcopy
DEFAULT_CATEGORIES=[
 {'id':'explanation','name':'Giải thích','color':'#b69af3'},
 {'id':'example','name':'Ví dụ minh họa','color':'#86bc83'},
 {'id':'counterargument','name':'Phản biện','color':'#ed997c'},
 {'id':'exception','name':'Ngoại lệ','color':'#e4c768'}]

def ensure_categories(board):
    if 'relation_categories' in board:return
    categories=deepcopy(DEFAULT_CATEGORIES);assignments=board.setdefault('edge_categories',{})
    for note,config in board.get('dossiers',{}).items():
        for side,groups in config.items():
            for group in groups:
                category=next((c for c in categories if c['name']==group['name']),None)
                if category is None:
                    category={'id':group['id'],'name':group['name'],'color':group.get('color','#b69af3')};categories.append(category)
                for other in group.get('members',[]):
                    pair=(note,other) if side=='out' else (other,note)
                    chosen=assignments.setdefault('\n'.join(pair),[])
                    if category['id'] not in chosen:chosen.append(category['id'])
    board['relation_categories']=categories


def merged_relations(window,note,side,all_boards=False):
    from dossier import legacy_related
    boards=window.boards.data['boards'] if all_boards else [window.boards.get(window.active_board)]
    legacy=legacy_related(window,note,side)
    result=[]
    for board in boards:
        ensure_categories(board)
        records=[]
        for source,target in board['edges']:
            if (side=='out' and source==note) or (side=='in' and target==note):
                style=board.get('edge_styles',{}).get(source+'\n'+target,{})
                records.append({'other':target if side=='out' else source,'pair':(source,target),'label':style.get('label',''),
                                'board':board['name'],'board_id':board['id'],'legacy':False})
        # Legacy references are displayed once in the current board's classification.
        if board['id']==window.active_board:
            pairs={r['pair'] for r in records}
            for item in legacy:
                if item['pair'] not in pairs:
                    records.append({**item,'label':board.get('edge_styles',{}).get('\n'.join(item['pair']),{}).get('label',''),'board':board['name'],'board_id':board['id']})
        for record in records:
            key='\n'.join(record['pair'])
            if key in board.get('hidden_references',[]):continue
            record['categories']=list(board.get('edge_categories',{}).get(key,[]))
            record['category_names']=[c['name'] for c in board['relation_categories'] if c['id'] in record['categories']]
            result.append(record)
    return result


def relation_label(board,pair):
    ensure_categories(board)
    chosen=board.get('edge_categories',{}).get('\n'.join(pair),[])
    names=[c['name'] for c in board['relation_categories'] if c['id'] in chosen]
    return ' · '.join(names) if names else 'Chưa phân loại'
