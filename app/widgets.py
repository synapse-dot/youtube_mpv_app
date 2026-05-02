import hashlib
import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPixmap
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout

from app.workers import WorkerSignals, ThumbnailWorker


class SearchResultItem(QWidget):
    def __init__(self, entry):
        super().__init__()
        self.entry = entry

        root = QHBoxLayout(self)
        root.setSpacing(14)

        self.thumb = QLabel()
        self.thumb.setFixedSize(168, 94)
        blank = QPixmap(168, 94)
        blank.fill(QColor("#20242f"))
        self.thumb.setPixmap(blank)
        self.thumb.setStyleSheet("background:#20242f; border:1px solid #3f4558; border-radius:8px;")
        root.addWidget(self.thumb)

        text = QVBoxLayout()
        title = QLabel(entry.get("title", "Unknown"))
        title.setObjectName("result_title")
        title.setWordWrap(True)
        text.addWidget(title)

        meta = []
        if entry.get("duration"):
            m, s = divmod(entry["duration"], 60)
            meta.append(f"{int(m)}:{int(s):02d}")
        if entry.get("uploader"):
            meta.append(entry["uploader"])
        if entry.get("upload_date"):
            try:
                d = datetime.strptime(entry["upload_date"], "%Y%m%d")
                meta.append(d.strftime("%Y-%m-%d"))
            except Exception:
                pass

        meta_lbl = QLabel(" • ".join(meta))
        meta_lbl.setObjectName("result_meta")
        text.addWidget(meta_lbl)

        root.addLayout(text)
        self._load_thumbnail()

    def _load_thumbnail(self):
        thumbs = self.entry.get("thumbnails", [])
        if not thumbs:
            return
        info = thumbs[-1]
        if not info.get("url"):
            return

        cache_dir = os.path.join(os.path.expanduser("~"), ".youtube_mpv_cache", "thumbs")
        os.makedirs(cache_dir, exist_ok=True)
        path = os.path.join(cache_dir, hashlib.md5(info["url"].encode()).hexdigest() + ".jpg")

        if os.path.exists(path):
            self._apply_thumbnail(path)
            return

        signals = WorkerSignals()
        signals.results.connect(self._apply_thumbnail)
        ThumbnailWorker(info["url"], path, signals).start()

    def _apply_thumbnail(self, path):
        pix = QPixmap(path)
        if pix.isNull():
            return
        pix = pix.scaled(168, 94, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        final = QPixmap(168, 94)
        final.fill(QColor("#20242f"))
        painter = QPainter(final)
        painter.drawPixmap((168 - pix.width()) // 2, (94 - pix.height()) // 2, pix)
        painter.end()
        self.thumb.setPixmap(final)
