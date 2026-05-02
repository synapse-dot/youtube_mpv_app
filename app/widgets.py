import hashlib
import os
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QColor, QPainter
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
        
        if t["name"] == "BRUTALIST":
            layout = QVBoxLayout(self.container)
            layout.setContentsMargins(20, 20, 20, 20)
            self.container.setStyleSheet(f"background: #fff; border: 6px solid #000; margin: 10px;")
        elif t["name"] == "VOGUE":
            layout = QHBoxLayout(self.container)
            layout.setContentsMargins(0, 40, 0, 40)
            self.container.setStyleSheet("border-bottom: 1px solid #dcdcdc;")
        else: # CYBERPUNK
            layout = QHBoxLayout(self.container)
            layout.setContentsMargins(15, 15, 15, 15)
            self.container.setStyleSheet(f"background: {t['item_bg']}; border-left: 5px solid {t['text']}; margin: 5px;")

        root.addWidget(self.container)

        self.thumb = QLabel()
        t_size = (240, 135) if t["name"] == "BRUTALIST" else (160, 90)
        self.thumb.setFixedSize(*t_size)
        self.thumb.setStyleSheet(f"background: #000; border: {t['border_width']} solid {t['border_color']};")
        layout.addWidget(self.thumb)

        text_v = QVBoxLayout()
        text_v.setSpacing(5)
        
        self.title_lbl = QLabel(self.entry.get("title", "NO_SIGNAL"))
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setStyleSheet(f"""
            color: {t['text'] if t['name'] != 'VOGUE' else t['text']};
            font-family: {t['font']};
            font-weight: 900;
            font-size: {'16pt' if t['name'] == 'BRUTALIST' else '12pt'};
            text-transform: {'uppercase' if t['name'] != 'VOGUE' else 'none'};
            letter-spacing: {'2px' if t['name'] == 'CYBERPUNK' else '0px'};
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

        cache_dir = os.path.join(os.path.expanduser("~"), ".youtube_mpv_cache", "thumbs")
        os.makedirs(cache_dir, exist_ok=True)
        path = os.path.join(cache_dir, hashlib.md5(url.encode()).hexdigest() + ".jpg")

        if os.path.exists(path):
            self._apply_thumbnail(path)
            return

        signals = WorkerSignals()
        signals.results.connect(self._apply_thumbnail)
        ThumbnailWorker(url, path, signals).start()

    def _apply_thumbnail(self, path):
        pix = QPixmap(path)
        if pix.isNull(): return
        pix = pix.scaled(self.thumb.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.thumb.setPixmap(pix)

class LoadingSpinner(QLabel):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self.chars = ["█", " ", "█", " "] if theme["name"] == "BRUTALIST" else ["◐", "◓", "◑", "◒"]
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
