# mpvtube.py
import sys
import os
import json
import subprocess
import threading
import urllib.request
import hashlib
from datetime import datetime

from yt_dlp import YoutubeDL
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QSpinBox, QListWidget, QListWidgetItem, QLabel, QDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QObject, QSize
from PySide6.QtGui import QFont, QPainter, QColor, QPixmap


# =========================
# Storage
# =========================

class StorageManager:
    def __init__(self):
        self.config_path = os.path.join(os.path.expanduser("~"), ".youtube_mpv_config.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "mpv_path": "mpv",
            "history": [],
            "favorites": [],
            "settings": {
                "default_quality": "best",
                "auto_start_last": False,
                "max_results": 10,
            },
        }

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def add_to_history(self, query):
        if query not in self.data["history"]:
            self.data["history"].insert(0, query)
            self.data["history"] = self.data["history"][:20]
            self.save()

    def get_setting(self, k, d=None):
        return self.data["settings"].get(k, d)


# =========================
# Signals
# =========================

class WorkerSignals(QObject):
    results = Signal(object)
    error = Signal(str)
    finished = Signal()


# =========================
# Thumbnail Worker
# =========================

class ThumbnailWorker(threading.Thread):
    def __init__(self, url, path, signals):
        super().__init__(daemon=True)
        self.url = url
        self.path = path
        self.signals = signals

    def run(self):
        try:
            urllib.request.urlretrieve(self.url, self.path)
            self.signals.results.emit(self.path)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


# =========================
# Search Worker
# =========================

class YTSearchWorker(threading.Thread):
    def __init__(self, query, max_results, signals):
        super().__init__(daemon=True)
        self.query = query
        self.max_results = max_results
        self.signals = signals

    def run(self):
        try:
            with YoutubeDL({"extract_flat": True, "skip_download": True}) as ydl:
                info = ydl.extract_info(
                    f"ytsearch{self.max_results}:{self.query}",
                    download=False
                )
                self.signals.results.emit(info.get("entries", []))
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


# =========================
# Result Widget
# =========================

class SearchResultItem(QWidget):
    def __init__(self, entry):
        super().__init__()
        self.entry = entry

        root = QHBoxLayout(self)
        root.setSpacing(12)

        self.thumb = QLabel()
        self.thumb.setFixedSize(160, 90)
        blank = QPixmap(160, 90)
        blank.fill(QColor("#000000"))
        self.thumb.setPixmap(blank)
        self.thumb.setStyleSheet("background:#000;border:1px solid #00ff88;")
        root.addWidget(self.thumb)

        text = QVBoxLayout()
        title = QLabel(entry.get("title", "Unknown"))
        title.setStyleSheet("color:#00ff88;font-weight:600;")
        title.setWordWrap(True)
        text.addWidget(title)

        meta = []
        if entry.get("duration"):
            m, s = divmod(entry["duration"], 60)
            meta.append(f"{int(m)}:{int(s):02d}")
        if entry.get("upload_date"):
            try:
                d = datetime.strptime(entry["upload_date"], "%Y%m%d")
                meta.append(d.strftime("%Y-%m-%d"))
            except Exception:
                pass

        meta_lbl = QLabel(" | ".join(meta))
        meta_lbl.setStyleSheet("color:#66ffcc;font-size:9pt;")
        text.addWidget(meta_lbl)

        root.addLayout(text)
        self._load_thumbnail()

    def _load_thumbnail(self):
        url = self.entry.get("thumbnail")
        if not url:
            return

        cache_dir = os.path.join(
            os.path.expanduser("~"), ".youtube_mpv_cache", "thumbs"
        )
        os.makedirs(cache_dir, exist_ok=True)

        name = hashlib.md5(url.encode()).hexdigest() + ".jpg"
        path = os.path.join(cache_dir, name)

        if os.path.exists(path):
            self._apply_thumbnail(path)
            return

        signals = WorkerSignals()
        signals.results.connect(self._apply_thumbnail)

        ThumbnailWorker(url, path, signals).start()

    def _apply_thumbnail(self, path):
        pix = QPixmap(path)
        if pix.isNull():
            return

        pix = pix.scaled(
            160, 90,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )

        final = QPixmap(160, 90)
        final.fill(QColor("#000000"))

        painter = QPainter(final)
        painter.drawPixmap(
            (160 - pix.width()) // 2,
            (90 - pix.height()) // 2,
            pix
        )
        painter.end()

        self.thumb.setPixmap(final)


# =========================
# Formats Worker
# =========================

class FormatsWorker(threading.Thread):
    def __init__(self, url, signals):
        super().__init__(daemon=True)
        self.url = url
        self.signals = signals

    def run(self):
        try:
            with YoutubeDL({"skip_download": True}) as ydl:
                info = ydl.extract_info(self.url, download=False)
                self.signals.results.emit(info.get("formats", []))
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


# =========================
# Main Window
# =========================

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.storage = StorageManager()
        self.last_format_id = None

        self.setWindowTitle("mpvTube")
        self.resize(1100, 800)
        self._style()

        v = QVBoxLayout(self)

        title = QLabel("mpvTube :: YouTube → mpv")
        title.setStyleSheet("color:#00ff88;font-size:20pt;")
        v.addWidget(title)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("search or paste url")
        self.search.returnPressed.connect(self.start_search)
        bar.addWidget(self.search)

        self.count = QSpinBox()
        self.count.setRange(1, 50)
        self.count.setValue(self.storage.get_setting("max_results", 10))
        bar.addWidget(self.count)

        btn = QPushButton("SEARCH")
        btn.clicked.connect(self.start_search)
        bar.addWidget(btn)

        v.addLayout(bar)

        self.results = QListWidget()
        self.results.itemActivated.connect(self.play_selected)
        v.addWidget(self.results)

    def _style(self):
        QApplication.instance().setFont(QFont("Courier New"))
        self.setStyleSheet("""
            QWidget { background:#0b0e14;color:#c0caf5; }
            QLineEdit,QSpinBox {
                background:#000;border:1px solid #00ff88;padding:6px;
                color:#00ff88;
            }
            QPushButton {
                background:#000;border:1px solid #00ff88;
                color:#00ff88;padding:6px;
            }
            QPushButton:hover { background:#003322; }
            QListWidget {
                background:#000;border:1px solid #00ff88;
            }
            QListWidget::item:selected {
                background:#003322;
            }
        """)

    def start_search(self):
        q = self.search.text().strip()
        if not q:
            return

        self.results.clear()
        self.storage.add_to_history(q)

        sig = WorkerSignals()
        sig.results.connect(self._populate)

        YTSearchWorker(q, self.count.value(), sig).start()

    def _populate(self, entries):
        for e in entries:
            item = QListWidgetItem()
            widget = SearchResultItem(e)
            item.setSizeHint(QSize(400, 100))
            item.setData(Qt.UserRole, e.get("webpage_url") or e.get("url"))
            self.results.addItem(item)
            self.results.setItemWidget(item, widget)

    def play_selected(self, item):
        url = item.data(Qt.UserRole)

        sig = WorkerSignals()
        sig.results.connect(lambda f: self.show_formats_dialog(url, f))
        sig.error.connect(lambda e: QMessageBox.critical(self, "Error", e))

        FormatsWorker(url, sig).start()

    def show_formats_dialog(self, url, formats):
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Quality")
        dlg.setStyleSheet(self.styleSheet())
        dlg.resize(500, 400)

        v = QVBoxLayout(dlg)
        listw = QListWidget()

        seen = set()
        for f in sorted(formats, key=lambda x: x.get("height", 0) or 0, reverse=True):
            fid = f.get("format_id")
            if not fid or fid in seen:
                continue
            seen.add(fid)

            label = f"{f.get('height','?')}p"
            if f.get("vcodec") == "none":
                label = f"audio {f.get('abr','')}kbps"

            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, fid)
            listw.addItem(it)

        listw.itemActivated.connect(
            lambda it: self._play_with_format(url, it.data(Qt.UserRole), dlg)
        )

        v.addWidget(QLabel("Double-click quality:"))
        v.addWidget(listw)
        dlg.exec()

    def _play_with_format(self, url, fmt, dlg):
        dlg.accept()
        os.execvp(
            self.storage.data["mpv_path"],
            [self.storage.data["mpv_path"], f"--ytdl-format={fmt}", url]
        )


# =========================
# Entry
# =========================

def main():
    app = QApplication([])
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()