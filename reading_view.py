"""Markdown rendering with explicit source blank-line preservation."""
import re
from PyQt6.QtGui import QTextDocument,QTextDocumentFragment,QTextCursor,QTextBlockFormat,QTextCharFormat

def render_markdown(view,text):
    document=view.document();document.clear()
    if not text:return
    cursor=QTextCursor(document);lines=text.split('\n');index=0;has_content=False
    while index<len(lines):
        if not lines[index].strip():
            start=index
            while index<len(lines) and not lines[index].strip():index+=1
            count=index-start
            breaks=count+(1 if has_content and index<len(lines) else 0)
            if not has_content and index==len(lines):breaks=max(0,count-1)
            for _ in range(breaks):cursor.insertBlock(QTextBlockFormat(),QTextCharFormat())
            continue
        block=[];fenced=False
        while index<len(lines):
            line=lines[index]
            if not line.strip() and not fenced:break
            if re.match(r'^\s*(```|~~~)',line):fenced=not fenced;block.append(line)
            else:block.append(line if fenced else line+'  ')
            index+=1
        fragment=QTextDocument()
        fragment.setDefaultStyleSheet('p { margin:0; }')
        fragment.setMarkdown('\n'.join(block))
        cursor.insertFragment(QTextDocumentFragment(fragment));has_content=True
    view.setTextCursor(QTextCursor(document))
