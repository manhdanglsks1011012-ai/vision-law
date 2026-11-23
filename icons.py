"""Small, consistent outline icons drawn locally; no font glyph dependency."""
from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor

def icon(name):
    image = QPixmap(24, 24)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor('#aaa9b0'), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    def line(a,b,c,d): p.drawLine(a,b,c,d)
    if name in ('folder','folder-plus'):
        for a in [(3,7,3,19),(3,19,21,19),(21,19,21,7),(21,7,11,7),(11,7,9,4),(9,4,3,4),(3,4,3,7)]: line(*a)
        if name=='folder-plus': line(9,13,15,13); line(12,10,12,16)
    elif name=='note':
        p.drawRoundedRect(QRectF(5,3,14,18),2,2); line(9,9,15,9); line(9,13,15,13); line(9,17,13,17)
    elif name=='search':
        p.drawEllipse(QRectF(4,3,12,12)); line(15,15,21,21)
    elif name=='settings':
        p.drawEllipse(QRectF(6,6,12,12)); p.drawEllipse(QRectF(10,10,4,4))
        for a in [(12,2,12,5),(12,19,12,22),(2,12,5,12),(19,12,22,12),(5,5,7,7),(17,17,19,19),(5,19,7,17),(17,7,19,5)]: line(*a)
    elif name=='sidebar':
        p.drawRoundedRect(QRectF(3,4,18,16),2,2); line(9,4,9,20)
        line(5,8,7,8);line(5,11,7,11)
    elif name=='board':
        for x,y in [(4,4),(14,4),(4,14),(14,14)]: p.drawRoundedRect(QRectF(x,y,6,6),1,1)
    elif name=='refresh':
        p.drawArc(QRectF(4,4,16,16),40*16,285*16); line(20,4,20,10); line(20,10,14,10)
    elif name=='collapse':
        line(6,5,12,10); line(12,10,18,5); line(6,19,12,14); line(12,14,18,19)
    elif name=='chevrons':
        line(8,8,12,4); line(12,4,16,8); line(8,16,12,20); line(12,20,16,16)
    p.end()
    return QIcon(image)
