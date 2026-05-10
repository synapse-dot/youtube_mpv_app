import hashlib
import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QFrame

from app.workers import WorkerSignals, ThumbnailWorker

class SearchResultItem(QWidget):
    def __init__(self, entry, theme):
        super().__init__()
        self.entry, self.theme = entry, theme
        self._init_ui()

    def _init_ui(self):
        t = self.theme
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame()
        self.container.setObjectName("item_container")
        
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(15, 15, 15, 15)
        self.container.setStyleSheet(f"background: {t['item_bg']}; border-left: 5px solid {t['accent']}; margin: 5px;")

        root.addWidget(self.container)

        self.thumb = QLabel()
        t_size = (160, 90)
        self.thumb.setFixedSize(*t_size)
        self.thumb.setStyleSheet(f"background: #000; border: {t['border_width']} solid {t['border_color']};")
        layout.addWidget(self.thumb)

        text_v = QVBoxLayout()
        text_v.setSpacing(5)
        
        self.title_lbl = QLabel(self.entry.get("title", "NO_SIGNAL"))
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setStyleSheet(f"""
            color: {t['text']};
            font-family: {t['font']};
            font-weight: 900;
            font-size: 12pt;
            text-transform: none;
            letter-spacing: 0px;
        """)
        text_v.addWidget(self.title_lbl)

        meta_str = f"{self.entry.get('uploader', 'UNKNOWN')} // {self.entry.get('duration_string', '0:00')}"
        self.meta_lbl = QLabel(meta_str)
        self.meta_lbl.setStyleSheet(f"""
            color: {t['accent']};
            font-family: {t['font']};
            font-size: 8pt;
            opacity: 0.8;
            text-transform: uppercase;
        """)
        text_v.addWidget(self.meta_lbl)
        
        layout.addLayout(text_v)
        self._load_thumbnail()

    def _load_thumbnail(self):
        thumbs = self.entry.get("thumbnails", [])
        if not thumbs: return
        url = thumbs[-1].get("url")
        if not url: return

        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "mpvTube", "thumbs")
        os.makedirs(cache_dir, exist_ok=True)
        path = os.path.join(cache_dir, hashlib.md5(url.encode()).hexdigest() + ".jpg")

        if os.path.exists(path):
            self._apply_thumbnail(path)
            return

        self.thumb_signals = WorkerSignals()
        self.thumb_signals.results.connect(self._apply_thumbnail)
        ThumbnailWorker(url, path, self.thumb_signals).start()

    def _apply_thumbnail(self, path):
        pix = QPixmap(path)
        if pix.isNull(): return
        pix = pix.scaled(self.thumb.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.thumb.setPixmap(pix)

class LoadingSpinner(QLabel):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self.chars = ["◐", "◓", "◑", "◒"]
        self.idx = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"color: {theme['accent']}; font-size: 24pt; font-family: {theme['font']};")

    def start(self): self.timer.start(150); self.show()
    def stop(self): self.timer.stop(); self.hide()
    def _update(self):
        self.setText(self.chars[self.idx])
        self.idx = (self.idx + 1) % len(self.chars)
