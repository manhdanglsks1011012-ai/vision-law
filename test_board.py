"""Run with QT_QPA_PLATFORM=offscreen python3 -m unittest -v."""
import tempfile
import unittest
from PyQt6.QtCore import QPointF, QSettings
from PyQt6.QtWidgets import QApplication, QGraphicsView
from app import Window
from storage import Vault
from theme import apply_theme

class BoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings_tmp = tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, cls.settings_tmp.name)
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)

    def test_moving_selected_card_keeps_geometry_and_edges_current(self):
        with tempfile.TemporaryDirectory() as directory:
            vault = Vault(directory)
            a, b = vault.create('A'), vault.create('B')
            vault.connect(a, b)
            window = Window(directory)
            try:
                window.show()
                self.app.processEvents()
                window.add_connection(a,b)
                board = window.board
                card = board.cards[a]
                card.setSelected(True)
                self.assertTrue(card.boundingRect().contains(card.rect().adjusted(-6, -6, 6, 6)))
                self.assertEqual(board.viewportUpdateMode(), QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
                count = len(board.scene().items())
                for i in range(80):
                    card.setPos(i * 4, (i % 13) * 9)
                    self.app.processEvents()
                    self.assertEqual(len(board.edges), 1)
                    self.assertEqual(len(board.scene().items()), count)
                    forward = board.cards[b].x() >= card.x()
                    expected = card.mapToScene(QPointF(260 if forward else 0, 52))
                    self.assertEqual(board.edges[0].path().pointAtPercent(0), expected)
                self.assertTrue(window.save_layout())
            finally:
                window.close()
