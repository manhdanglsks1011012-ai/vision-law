"""Release startup, local logs and recovery copies of unsaved documents."""
import json,logging,sys,traceback,os
from datetime import datetime,timezone
from pathlib import Path
from PyQt6.QtCore import QStandardPaths
from storage import atomic_write
from version import VERSION

def data_dir():
    folder=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    folder.mkdir(parents=True,exist_ok=True);return folder

def default_vault():
    from preferences import Preferences
    for value in Preferences().get('recent_vaults',[]):
        path=Path(value)
        if path.is_dir():return path
    folder=data_dir()/'First vault';folder.mkdir(parents=True,exist_ok=True)
    note=folder/'Chào mừng.md'
    if not note.exists():
        note.write_text('# Chào mừng\n\nVision law '+VERSION+'\n\nĐây là vault đầu tiên, lưu trên máy của bạn.\n\nTạo ghi chú, đặt lên bảng và nối các khái niệm.\n',encoding='utf-8')
    return folder

def configure_logging():
    from logging.handlers import RotatingFileHandler
    directory=data_dir()/'logs';directory.mkdir(exist_ok=True)
    handler=RotatingFileHandler(directory/'vision-law.log',maxBytes=1_000_000,backupCount=3,encoding='utf-8')
    logging.basicConfig(level=logging.INFO,handlers=[handler],format='%(asctime)s %(levelname)s %(message)s')
    logging.info('Vision law %s startup',VERSION)
    def exception_hook(kind,value,tb):
        logging.error('Unhandled error',exc_info=(kind,value,tb))
        # Do not abort Qt's event loop or silently discard open drafts.
        from PyQt6.QtWidgets import QMessageBox,QApplication
        app=QApplication.instance();window=getattr(app,'vision_window',None)
        if window:
            try:save_recovery(window)
            except Exception:logging.exception('Could not preserve recovery copy')
        message=QMessageBox(QMessageBox.Icon.Critical,'Vision law',
            'Một thao tác chưa hoàn tất. Nội dung đang mở được giữ lại.\nChi tiết đã ghi trong '+str(directory/'vision-law.log'))
        if app:
            app._error_message=message;message.show()
        else:sys.__excepthook__(kind,value,tb)
    sys.excepthook=exception_hook

def save_recovery(window):
    directory=data_dir()/'recovery'
    vault=str(window.vault.root) if window.vault else ''
    import hashlib
    key=hashlib.sha256(vault.encode()).hexdigest()[:16]
    documents=[]
    for doc in window.documents.values():
        if doc.input.toPlainText()!=doc.saved_source or doc.title_field.text()!=doc.card_title or doc.summary_field.text()!=doc.card_summary:
            documents.append({'path':doc.name,'title':doc.title_field.text(),'summary':doc.summary_field.text(),
                'body':doc.input.toPlainText(),'heading_prefix':getattr(doc,'body_heading_prefix','')})
    target=directory/(key+'.json')
    if documents:
        atomic_write(target,json.dumps({'version':1,'vault':vault,'saved':datetime.now(timezone.utc).isoformat(),'documents':documents},ensure_ascii=False,indent=2))
    elif target.exists():target.unlink()

def offer_recovery(window):
    import hashlib
    from PyQt6.QtWidgets import QMessageBox
    if not window.vault:return
    key=hashlib.sha256(str(window.vault.root).encode()).hexdigest()[:16]
    target=data_dir()/'recovery'/(key+'.json')
    if not target.exists():return
    try:payload=json.loads(target.read_text(encoding='utf-8'))
    except Exception:
        logging.exception('Could not read recovery data');return
    if payload.get('vault')!=str(window.vault.root) or not payload.get('documents'):return
    answer=QMessageBox.question(window,'Bản nháp từ phiên trước',
        'Tìm thấy '+str(len(payload['documents']))+' bản nháp chưa lưu. Khôi phục vào vùng soạn thảo để kiểm tra?\n'
        'Chọn Không vẫn giữ một bản sao trong thư mục recovery.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
    # Archive first; recovery never overwrites a Markdown file directly.
    archive=target.with_name(target.stem+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.archive.json')
    target.rename(archive)
    if answer==QMessageBox.StandardButton.Yes:
        for item in payload['documents']:
            try:
                if not all(isinstance(item.get(k),str) for k in ('path','title','summary','body')):continue
                if not window.vault.path(item['path']).exists():continue
                window.edit(item['path']);doc=window.documents.get(item['path'])
                if doc:
                    doc.title_field.setText(item['title']);doc.summary_field.setText(item['summary']);doc.input.setPlainText(item['body'])
                    doc.autosave_timer.stop();doc.message.setText('Bản nháp khôi phục — chưa ghi vào tệp')
            except Exception:logging.exception('Could not restore a draft')
    logging.info('Previous drafts archived at %s',archive)
