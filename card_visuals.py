import json
import re
import math
from pathlib import Path
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPen, QPainterPath, QFont, QFontMetricsF, QPolygonF
from PyQt6.QtWidgets import QGraphicsPathItem

OLD_TIER_COLORS=['#ad8aff','#61b5ff','#49d4c6','#87cf74','#ddce69','#f5b469','#ed8f79','#e98bc0','#ac9de8','#9ba9ba']
PREVIOUS_TIER_COLORS=['#f06464','#f39452','#e7b94f','#e4d66a','#e58abb','#b18aff','#6aabf5','#5acbd0','#86bc83','#9ba0a8']
COLORS=['#f06464','#e58abb','#f39452','#e7b94f','#e4d66a','#b18aff','#6aabf5','#5acbd0','#86bc83','#9ba0a8']
TIER_NAMES=['Đỏ','Hồng','Cam','Vàng kim','Vàng nhạt','Tím','Xanh dương','Xanh ngọc','Xanh lá','Xám']
TIER_MODULES=['LEGENDARY MODULE','MYTHIC MODULE','ANCIENT MODULE','EXALTED MODULE','EXCEPTIONAL MODULE','EPIC MODULE','RARE MODULE','REFINED MODULE','UNCOMMON MODULE','NORMAL MODULE']
META=re.compile(r'^<!-- vision-law-card: (.*?) -->\n?',re.M)
def details(text,name):
    match=META.search(text)
    try: data=json.loads(match[1]) if match else {}
    except (ValueError,TypeError): data={}
    return str(data.get('title',Path(name).stem)),str(data.get('summary',''))
def with_details(text,title,summary):
    text=META.sub('',text)
    return '<!-- vision-law-card: '+json.dumps({'title':title,'summary':summary},ensure_ascii=False).replace('-->','--\\u003e')+' -->\n'+text

def style_for(window,name):
    if not window.boards or not window.active_board: return {'tier':1,'color':COLORS[0]}
    data=window.boards.get(window.active_board).get('styles',{}).get(name,{})
    tier=max(1,min(10,int(data.get('tier',1))))
    return {'tier':tier,'color':data.get('color',COLORS[tier-1])}

def orthogonal_path(a,b,source_side='right'):
    path=QPainterPath(a)
    if abs(a.x()-b.x())<0.01 or abs(a.y()-b.y())<0.01:
        path.lineTo(b)
    else:
        corner=QPointF(a.x(),b.y()) if source_side in ('top','bottom') else QPointF(b.x(),a.y())
        path.lineTo(corner)
        path.lineTo(b)
    return path

class Pipe(QGraphicsPathItem):
    def __init__(self,path,color,board,label='',note=''):
        super().__init__(path)
        self.color=QColor(color); self.board=board
        self.label=label
        self.note=note
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setPen(QPen(self.color,10,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        self.setZValue(-1)
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            self.board.edit_connection(self.data(0));event.accept();return
        super().mousePressEvent(event)

    def text_rect(self,text,below=False):
        from PyQt6.QtCore import QRectF
        path=self.path()
        horizontal=[]
        for i in range(1,path.elementCount()):
            a,b=path.elementAt(i-1),path.elementAt(i)
            if abs(a.y-b.y)<0.01 and abs(a.x-b.x)>0.01:
                horizontal.append((abs(a.x-b.x),QPointF((a.x+b.x)/2,a.y)))
        if horizontal:
            center=max(horizontal,key=lambda segment:segment[0])[1]
        else:
            a,b=path.pointAtPercent(0),path.pointAtPercent(1)
            center=QPointF((a.x()+b.x())/2,max(a.y(),b.y()))
        font=QFont('Sans Serif',9)
        width=min(360,QFontMetricsF(font).horizontalAdvance(text)+20)
        return QRectF(center.x()-width/2,center.y()+12 if below else center.y()-40,width,28)

    def label_rect(self):return self.text_rect(self.label)

    def note_rect(self):return self.text_rect(self.note,True)

    def boundingRect(self):
        rect=super().boundingRect().adjusted(-6,-6,6,6)
        if self.label:rect=rect.united(self.label_rect())
        if self.note:rect=rect.united(self.note_rect())
        return rect

    def shape(self):
        from PyQt6.QtGui import QPainterPathStroker
        stroker=QPainterPathStroker();stroker.setWidth(20)
        path=stroker.createStroke(self.path())
        if self.label: path.addRect(self.label_rect())
        if self.note:path.addRect(self.note_rect())
        return path

    def paint(self,painter,option,widget=None):
        path=self.path()
        painter.setPen(QPen(self.color.darker(260),11,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)); painter.drawPath(path)
        painter.setPen(QPen(self.color.darker(140),7,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)); painter.drawPath(path)
        painter.setPen(QPen(self.color.lighter(120),1)); painter.drawPath(path)
        length=path.length()
        if length < 1: return
        painter.setPen(QPen(self.color.lighter(150),1.8,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        for i in range(max(1,int(length/65))):
            distance=(i*65+self.board.flow_phase)%length
            t=path.percentAtLength(distance)
            point=path.pointAtPercent(t)
            before=path.pointAtPercent(path.percentAtLength(max(0,distance-1)))
            after=path.pointAtPercent(path.percentAtLength(min(length,distance+1)))
            angle=math.atan2(after.y()-before.y(),after.x()-before.x())
            for offset in (-0.65,0.65):
                end=QPointF(point.x()-5*math.cos(angle+offset),point.y()-5*math.sin(angle+offset))
                painter.drawLine(point,end)

        for content,rect in [(self.label,self.label_rect()),(self.note,self.note_rect())]:
            if not content:continue
            painter.setPen(QPen(self.color,1))
            painter.setBrush(QColor('#25232d'))
            painter.drawRoundedRect(rect,5,5)
            painter.setFont(QFont('Sans Serif',9));painter.setPen(self.color.lighter(140))
            text=QFontMetricsF(painter.font()).elidedText(content,Qt.TextElideMode.ElideRight,rect.width()-16)
            painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,text)
