"""Direct Markdown editing with live block/inline styling and editing commands."""
import re
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QSyntaxHighlighter,QTextCharFormat,QColor,QFont,QTextCursor,QKeySequence
from PyQt6.QtWidgets import QPlainTextEdit

class MarkdownStyle(QSyntaxHighlighter):
    def __init__(self,editor):
        super().__init__(editor.document());self.editor=editor
    def highlightBlock(self,text):
        current=self.currentBlock().blockNumber()==self.editor.textCursor().blockNumber()
        base=QTextCharFormat();base.setForeground(QColor('#dedbe5'))
        self.setFormat(0,len(text),base)
        def fmt(start,length,color=None,bold=False,italic=False,size=None):
            style=QTextCharFormat()
            if color:style.setForeground(QColor(color))
            if bold:style.setFontWeight(QFont.Weight.Bold)
            if italic:style.setFontItalic(True)
            if size:style.setFontPointSize(max(2,size))
            self.setFormat(start,length,style)
        # Fenced code remains literal; do not apply inline markup within it.
        fence=re.match(r'^\s*(```+|~~~+)',text)
        in_code=self.previousBlockState()==1
        self.setCurrentBlockState(1 if (fence and not in_code) or (in_code and not fence) else 0)
        if fence or in_code:
            fmt(0,len(text),'#d4b78d')
            return
        heading=re.match(r'^(#{1,6})\s+',text)
        if heading:
            size=[23,20,17,15,14,13][len(heading[1])-1]
            fmt(0,len(text),'#eee8f8',True,size=size)
            fmt(0,heading.end(),'#92849f',size=12 if current else 2)
        for match in re.finditer(r'(\*\*|__)(.+?)\1',text):
            fmt(match.start(),len(match[0]),bold=True)
            fmt(match.start(),2,'#8b799d',size=12 if current else 2)
            fmt(match.end()-2,2,'#8b799d',size=12 if current else 2)
        for match in re.finditer(r'(?<!\*)\*([^*]+)\*(?!\*)',text):
            fmt(match.start(),len(match[0]),italic=True)
        for match in re.finditer(r'`[^`]+`',text):fmt(match.start(),len(match[0]),'#d4b78d')
        for pattern in (r'(?<![\w_])_([^_]+)_(?![\w_])',):
            for match in re.finditer(pattern,text):fmt(match.start(),len(match[0]),italic=True)
        for pattern,kind in [(r'~~(.+?)~~','strike'),(r'==(.+?)==','highlight'),(r'<u>(.+?)</u>','underline')]:
            for match in re.finditer(pattern,text):
                start,end=match.span(1)
                style=QTextCharFormat()
                if kind=='strike':style.setFontStrikeOut(True)
                if kind=='highlight':style.setBackground(QColor('#665522'));style.setForeground(QColor('#fff1bb'))
                if kind=='underline':style.setFontUnderline(True)
                self.setFormat(start,end-start,style)
                fmt(match.start(),start-match.start(),'#8b799d',size=12 if current else 2)
                fmt(end,match.end()-end,'#8b799d',size=12 if current else 2)
        for match in re.finditer(r'(?<!\\)%%.*?%%',text):
            fmt(match.start(),len(match[0]),'#77717e',italic=True)
        if text.startswith('>'):fmt(0,len(text),'#b1a2c5',italic=True)
        if re.match(r'^\s*([-*+] |\d+[.)] )',text):
            match=re.match(r'^\s*([-*+] |\d+[.)] )',text);fmt(0,match.end(),'#ba99ed')
        # Keep normal glyph metrics for hidden legacy links. Sub-pixel fonts
        # can trap Qt's text layout when opening/wrapping these paragraphs.
        for match in re.finditer(r'!?\[\[[^\]]+\]\]',text):fmt(match.start(),len(match[0]),'#1e1e1e')
        if text.startswith('<!-- vision-law-card:'):
            fmt(0,len(text),'#77717e',size=2)

class LiveEditor(QPlainTextEdit):
    def __init__(self,text='',parent=None):
        super().__init__(text,parent)
        self.setPlaceholderText('Viết nội dung ở đây…\n\n# Tiêu đề   **In đậm**   - Danh sách')
        self.highlighter=MarkdownStyle(self)
        self._highlighted_cursor_block=self.textCursor().blockNumber()
        self.cursorPositionChanged.connect(self.refresh_cursor_blocks)
        self.setTabStopDistance(28)

    def refresh_cursor_blocks(self):
        current=self.textCursor().blockNumber()
        if current==self._highlighted_cursor_block:return
        old=self._highlighted_cursor_block;self._highlighted_cursor_block=current
        for number in (old,current):
            block=self.document().findBlockByNumber(number)
            if block.isValid():self.highlighter.rehighlightBlock(block)

    def wrap(self,marker):
        cursor=self.textCursor();selected=cursor.selectedText().replace('\u2029','\n')
        closing='</u>' if marker=='<u>' else marker
        cursor.beginEditBlock()
        if selected.startswith(marker) and selected.endswith(closing) and len(selected)>=len(marker)+len(closing):
            cursor.insertText(selected[len(marker):-len(closing)])
        else:
            cursor.insertText(marker+selected+closing)
            if not selected:cursor.movePosition(QTextCursor.MoveOperation.Left,QTextCursor.MoveMode.MoveAnchor,len(closing))
        cursor.endEditBlock();self.setTextCursor(cursor)

    def indent(self,outdent=False):
        cursor=self.textCursor();start,end=cursor.selectionStart(),cursor.selectionEnd()
        first=self.document().findBlock(start);last=self.document().findBlock(end)
        if end>start and end==last.position():last=last.previous()
        blocks=[];block=first
        while block.isValid():
            blocks.append(block)
            if block==last:break
            block=block.next()
        cursor.beginEditBlock()
        for block in reversed(blocks):
            c=QTextCursor(block)
            if outdent:
                match=re.match(r'^( {1,4}|\t)',block.text())
                if match:
                    c.movePosition(QTextCursor.MoveOperation.Right,QTextCursor.MoveMode.KeepAnchor,len(match[0]));c.removeSelectedText()
            else:c.insertText('    ')
        cursor.endEditBlock()


    def heading(self,level):
        cursor=self.textCursor();cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,QTextCursor.MoveMode.KeepAnchor)
        text=re.sub(r'^#{1,6}\s+','',cursor.selectedText())
        cursor.insertText('#'*level+' '+text);cursor.endEditBlock()

    def keyPressEvent(self,event):
        ctrl=bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if ctrl and event.key() in (Qt.Key.Key_B,Qt.Key.Key_I):
            self.wrap({Qt.Key.Key_B:'**',Qt.Key.Key_I:'*'}[event.key()]);return
        if ctrl and Qt.Key.Key_1<=event.key()<=Qt.Key.Key_6:
            self.heading(event.key()-Qt.Key.Key_1+1);return
        if event.key() in (Qt.Key.Key_Tab,Qt.Key.Key_Backtab) and not ctrl:
            self.indent(event.key()==Qt.Key.Key_Backtab or bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier));return
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and not event.modifiers():
            cursor=self.textCursor();text=cursor.block().text()
            match=re.match(r'^(\s*)([-*+] |\d+[.)] |>{1,}\s)(\[[ xX]\]\s)?(.*)$',text)
            if match and cursor.atBlockEnd() and not cursor.hasSelection():
                indent,bullet,task,body=match.groups()
                if not body.strip():
                    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock,QTextCursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText();self.setTextCursor(cursor);return
                if re.match(r'\d',bullet):bullet=re.sub(r'\d+',lambda m:str(int(m[0])+1),bullet,count=1)
                cursor.insertText('\n'+indent+bullet+('[ ] ' if task else ''));self.setTextCursor(cursor);return
        super().keyPressEvent(event)
