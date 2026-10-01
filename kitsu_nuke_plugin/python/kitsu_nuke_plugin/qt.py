"""Qt binding shim for the classes this plugin uses.

Nuke bundles its own Qt binding — PySide6 from Nuke 16 on (Qt 6.5),
PySide2 in Nuke 11-15 — so, like the Maya version of this plugin, the
binding can't be imported directly by name. Every other module imports
its Qt classes from here instead, keeping them binding-agnostic.

PySide6 keeps the short-form enum spellings (Qt.AlignTop,
QLineEdit.Password, ...) working alongside the fully-qualified ones, so
the rest of the code doesn't need per-binding branches either.
"""

try:  # Nuke 16+
    from PySide6.QtCore import QObject, QRectF, QSettings, Qt, QTimer, Signal
    from PySide6.QtGui import (
        QBrush,
        QColor,
        QFont,
        QFontMetricsF,
        QPainter,
        QPainterPath,
        QPen,
        QPixmap,
    )
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # Nuke 11-15
    from PySide2.QtCore import QObject, QRectF, QSettings, Qt, QTimer, Signal
    from PySide2.QtGui import (
        QBrush,
        QColor,
        QFont,
        QFontMetricsF,
        QPainter,
        QPainterPath,
        QPen,
        QPixmap,
    )
    from PySide2.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QTextEdit,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )


def exec_dialog(dialog):
    """QDialog.exec() on PySide6, QDialog.exec_() on PySide2 — `exec` was
    a reserved word in Python 2, so PySide2/PyQt5 only expose the
    trailing-underscore spelling; Qt6 bindings dropped it in favor of the
    plain name."""
    if hasattr(dialog, "exec"):
        return dialog.exec()
    return dialog.exec_()
