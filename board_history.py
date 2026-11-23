"""Bounded, session-only snapshots of a visual board and its camera."""
from copy import deepcopy
from PyQt6.QtCore import QTimer,QPointF

class BoardHistory:
    def __init__(self,board):
        self.board=board;self.tim=QTimer(board);self.tim.setSingleShot(True);self.tim.setInterval(350)
        self.tim.timeout.connect(self.commit);self.entries={};self.restoring=False;self.key=None
    def snapshot(self):
        window=self.board.window
        if not window.boards or not window.active_board:return None
        data=deepcopy(window.boards.get(window.active_board))
        # A drag may not yet have reached the debounced disk save.
        positions=data['positions']
        for name,card in self.board.cards.items():positions[name]=[round(card.x(),4),round(card.y(),4)]
        center=self.board.mapToScene(self.board.viewport().rect().center())
        scale=round(self.board.transform().m11(),7);position=[round(center.x(),3),round(center.y(),3)]
        data['view']={'scale':scale,'center':position}
        return {'data':data,'scale':scale,'center':position}
    def activate(self):
        self.tim.stop()
        window=self.board.window
        self.key=(str(window.vault.root),window.active_board) if window.vault else None
        if self.key:
            snapshot=self.snapshot()
            if self.key not in self.entries:self.entries[self.key]=([snapshot],0)
            else:
                states,index=self.entries[self.key]
                # Opening a board is not an undoable edit.
                states[index]=snapshot
    def changed(self):
        if not self.restoring and self.key:self.tim.start()
    def commit(self):
        if self.restoring or not self.key:return
        snapshot=self.snapshot()
        states,index=self.entries[self.key]
        if snapshot!=states[index]:
            states=states[:index+1]+[snapshot]
            if len(states)>100:states=states[-100:]
            self.entries[self.key]=(states,len(states)-1)
    def step(self,delta):
        if not self.key:return
        self.tim.stop();self.commit()
        states,index=self.entries[self.key];target=index+delta
        if not 0<=target<len(states):return
        state=deepcopy(states[target]);window=self.board.window
        if not window.close_documents():return
        self.restoring=True
        try:
            self.board.cancel_connection();self.board.cancel_edge_click()
            data=window.boards.get(window.active_board);data.clear();data.update(state['data'])
            self.board.show_palette(None);self.board.cards,self.board.edges={},[];self.board.scene().clear()
            from app import Card
            for name,position in data['positions'].items():
                if name not in window.names:continue
                card=Card(self.board,name,position);self.board.cards[name]=card;self.board.scene().addItem(card)
            window.refresh_links()
            self.board.resetTransform();self.board.scale(state['scale'],state['scale'])
            self.board.centerOn(QPointF(*state['center']))
            data['view']={'scale':state['scale'],'center':state['center']}
            window.boards.save();window.update_zoom_display()
            self.entries[self.key]=(states,target)
            # Scrollbar rounding must not create a phantom edit on next undo.
            states[target]=self.snapshot()
        finally:self.restoring=False
        window.statusBar().showMessage('Hoàn tác bảng' if delta<0 else 'Làm lại bảng')
