import hashlib
import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QFrame

from app.workers import WorkerSignals, ThumbnailWorker

class SearchResultItem(QWidget):
    def __init__(self, entry, theme):
        super().__init__()
        self.entry = entry
        self.theme = theme
        self._init_ui()

    def _init_ui(self):
        t = self.theme
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame()
        self.container.setObjectName("item_container")
        
        # Structure changes based on theme
        if t["name"] == "BRUTALIST":
            layout = QVBoxLayout(self.container)
            layout.setContentsMargins(20, 20, 20, 20)
            self.container.setStyleSheet(f"background: {t['bg']}; border: {t['border']};")
        elif t["name"] == "VOGUE":
            layout = QHBoxLayout(self.container)
            layout.setContentsMargins(0, 30, 0, 30)
            self.container.setStyleSheet(f"border-bottom: 0.5px solid #dcdcdc;")
        else: # CYBERPUNK
            layout = QHBoxLayout(self.container)
            layout.setContentsMargins(10, 10, 10, 10)
            self.container.setStyleSheet(f"background: {t['item_bg']}; border-left: 4px solid {t['text']};")

        root.addWidget(self.container)

        self.thumb = QLabel()
        thumb_size = (180, 101) if t["name"] == "BRUTALIST" else (140, 78)
        self.thumb.setFixedSize(*thumb_size)
        self.thumb.setStyleSheet(f"background: #000; border: {t.get('item_border', 'none')};")
        layout.addWidget(self.thumb)

        text_v = QVBoxLayout()
        self.title_lbl = QLabel(self.entry.get("title", "UNKNOWN"))
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setStyleSheet(f"""
            color: {t['text'] if t['name'] != 'VOGUE' else t['text_alt']};
            font-family: {t['font']};
            font-weight: bold;
            font-size: {'14pt' if t['name'] == 'BRUTALIST' else '11pt'};
            text-transform: {'uppercase' if t['name'] == 'BRUTALIST' else 'none'};
        """)
        text_v.addWidget(self.title_lbl)

        meta = QLabel(f"{self.entry.get('uploader', '')} // {self.entry.get('duration_string', '')}")
        meta.setStyleSheet(f"color: {t['accent']}; font-family: {t['font']}; font-size: 8pt;")
        text_v.addWidget(meta)
        
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
        size = self.thumb.size()
        pix = pix.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.thumb.setPixmap(pix)

class LoadingSpinner(QLabel):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self.chars = ["█", "▓", "▒", "░", " "] if theme["name"] == "BRUTALIST" else ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.idx = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"color: {theme['accent']}; font-size: 24pt;")

    def start(self): self.timer.start(100); self.show()
    def stop(self): self.timer.stop(); self.hide()
    def _update(self):
        self.setText(self.chars[self.idx])
        self.idx = (self.idx + 1) % len(self.chars)
