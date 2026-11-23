from PyQt6.QtGui import QFont, QFontDatabase, QPalette, QColor

STYLE = '''
QWidget { background: #1e1e1e; color: #dcddde; font-size: 13px; }
QMainWindow, QDialog { background: #1e1e1e; }
QWidget#ribbon { background: #181818; border-right: 1px solid #303030; }
QWidget#sidebar { background: #262626; border-right: 1px solid #303030; }
QMdiSubWindow#noteSubWindow { background: #1e1e1e; border: 1px solid #49424f; border-radius: 8px; }
QTabWidget#noteTabs::pane { border: none; }
QTabWidget#noteTabs QTabBar::tab { padding: 6px 12px; min-width: 80px; max-width: 210px; border-top: 2px solid transparent; border-right: 1px solid #303030; }
QTabWidget#noteTabs QTabBar::tab:selected { background: #252329; border-top-color: #a88bfa; }
QWidget#writingPage { background: #1e1e1e; }
QLineEdit#inlineNoteTitle { background: transparent; border: none; border-radius: 0; padding: 0 0 5px 0; font-size: 27px; font-weight: 700; color: #ece8f1; }
QLineEdit#inlineNoteSummary { background: transparent; border: none; border-radius: 0; padding: 0 0 8px 0; font-size: 14px; color: #9f99a9; }
QLabel#saveState { color: #827b8b; font-size: 11px; background: transparent; }
QScrollArea#relationsPanel { border: none; background: #202024; }
QFrame#windowPicker { background: #27232f; border: 2px solid #a88bfa; border-radius: 10px; }
QFrame#windowPicker QListWidget { background: #211d29; border: none; }
QFrame#windowPicker QListWidget::item:selected { background: #51416c; border: 2px solid #bd9ef6; border-radius: 6px; }
QWidget#documentSheet { background: #1e1e1e; border: 1px solid #4a4059; border-radius: 8px; }
QWidget#referenceRow { background: transparent; border: none; }
QWidget#referenceRow:hover { background: #302b38; border-radius: 4px; }
QLabel#referenceLink { background: transparent; border: none; font-size: 13px; padding: 3px 0; }
QPushButton#addReference { text-align: left; padding: 1px 7px; color: #81768f; font-size: 15px; }
QPushButton#addReference:hover { color: #d2b9fb; }
QFrame#relationGroup { background: #25232b; border: 1px solid #44404d; border-radius: 7px; }
QFrame#relationCard { background: #1e1d24; border: 1px solid #37333f; border-radius: 5px; }
QFrame#relationCard QLabel { background: transparent; border: none; }
QPushButton#relationTitle { text-align: left; color: #c6a9ff; font-weight: 600; }
QLabel#sectionTitle { color: #b9a5dc; font-weight: 600; padding: 8px; }
QWidget#cardPalette { background: #25232b; border: 1px solid #51465e; border-radius: 8px; }
QWidget#cardPalette QLabel { background: transparent; border: none; }
QWidget#tabbar { background: #181818; border-bottom: 1px solid #303030; }
QTabBar::tab { background: #181818; color: #a6a3ab; padding: 11px 20px; border-right: 1px solid #303030; border-top: 2px solid transparent; }
QTabBar::tab:selected { background: #1e1e1e; color: #e2dbea; border-top: 2px solid #a88bfa; }
QTabBar::tab:hover { background: #29262e; }
QLabel#tab { background: #1e1e1e; border-top: 2px solid #a88bfa; padding: 12px 22px; }
QLabel#muted { color: #999999; background: transparent; }
QLabel#heading { font-size: 20px; font-weight: 600; background: transparent; }
QLabel#vault { font-weight: 600; padding: 12px 4px; background: transparent; }
QPushButton { background: transparent; border: 1px solid transparent; border-radius: 5px; padding: 7px 10px; color: #b3b3b3; }
QPushButton:hover { background: #353535; color: #fafafa; }
QPushButton:pressed { background: #483b65; }
QPushButton#primary { background: #7f5cc4; color: white; padding: 8px 18px; }
QPushButton#ribbonButton { font-size: 20px; padding: 8px 0; }
QLineEdit { background: #1e1e1e; border: 1px solid #363636; border-radius: 5px; padding: 7px 9px; selection-background-color: #574376; }
QLineEdit:focus { border-color: #9274d0; }
QTreeWidget { background: #262626; border: none; outline: none; padding: 4px; }
QTreeWidget::item { padding: 5px 2px; border-radius: 5px; }
QTreeWidget::item:selected { background: #40364f; color: #ece4ff; }
QTreeWidget::item:hover { background: #303030; }
QPlainTextEdit, QTextBrowser { background: #1e1e1e; border: 1px solid #333333; border-radius: 6px; padding: 18px; font-size: 15px; selection-background-color: #574376; }
QSplitter::handle { background: #303030; width: 1px; }
QGraphicsView { border: none; }
QStatusBar { background: #181818; border-top: 1px solid #303030; color: #999999; font-size: 12px; }
QScrollBar:vertical { background: transparent; width: 9px; }
QScrollBar::handle:vertical { background: #464646; border-radius: 4px; min-height: 30px; }
QScrollBar:horizontal { background: transparent; height: 9px; }
QScrollBar::handle:horizontal { background: #464646; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QMenu { background: #262626; border: 1px solid #454545; padding: 5px; }
QMenu::item { padding: 8px 18px; }
QMenu::item:selected { background: #40364f; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #77717f; border-radius: 3px; background: #242127; }
QCheckBox::indicator:checked { background: #9274d0; border-color: #b59ce8; }
QComboBox, QSpinBox { padding: 5px; border: 1px solid #444; border-radius: 4px; }
QToolTip { background: #303030; color: #eeeeee; border: 1px solid #555555; padding: 5px; }
'''

def apply_theme(app):
    app.setStyle('Fusion')
    palette=app.palette()
    palette.setColor(QPalette.ColorRole.Highlight,QColor('#70558f'))
    palette.setColor(QPalette.ColorRole.HighlightedText,QColor('#f5efff'))
    palette.setColor(QPalette.ColorRole.Window,QColor('#232127'))
    palette.setColor(QPalette.ColorRole.WindowText,QColor('#ded9e6'))
    palette.setColor(QPalette.ColorRole.Button,QColor('#302c37'))
    palette.setColor(QPalette.ColorRole.ButtonText,QColor('#ded9e6'))
    app.setPalette(palette)
    available = set(QFontDatabase.families())
    family = next((f for f in ('Inter', 'Noto Sans', 'DejaVu Sans') if f in available), 'Sans Serif')
    app.setFont(QFont(family, 10))
    app.setStyleSheet(STYLE)
