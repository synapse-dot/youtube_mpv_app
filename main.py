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
            req = urllib.request.Request(
                self.url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            with urllib.request.urlopen(req) as response:
                with open(self.path, 'wb') as f:
                    f.write(response.read())
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
        thumbnails = self.entry.get("thumbnails", [])
        if not thumbnails:
            return

        # Get the best quality thumbnail (usually the last one)
        thumb_info = thumbnails[-1] if thumbnails else None
        if not thumb_info or not thumb_info.get("url"):
            return

        url = thumb_info["url"]

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
        try:
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
        except Exception:
            pass  # Ignore errors, perhaps widget deleted


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
        try:
            for e in entries:
                item = QListWidgetItem()
                widget = SearchResultItem(e)
                item.setSizeHint(QSize(400, 100))
                item.setData(Qt.UserRole, e.get("webpage_url") or e.get("url"))
                self.results.addItem(item)
                self.results.setItemWidget(item, widget)
        except Exception:
            pass  # Ignore if UI deleted

    def play_selected(self, item):
        url = item.data(Qt.UserRole)

        sig = WorkerSignals()
        sig.results.connect(lambda f: self.show_formats_dialog(url, f))
        sig.error.connect(lambda e: QMessageBox.critical(self, "Error", e))

        FormatsWorker(url, sig).start()

    def show_formats_dialog(self, url, formats):
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("Select Quality")
            dlg.setStyleSheet(self.styleSheet())
            dlg.resize(700, 500)

            v = QVBoxLayout(dlg)
            
            # Video formats section
            v.addWidget(QLabel("Video Quality:"))
            video_list = QListWidget()
            video_list.setMaximumHeight(200)
            
            # Audio formats section  
            v.addWidget(QLabel("Audio Quality:"))
            audio_list = QListWidget()
            audio_list.setMaximumHeight(150)
            
            # Separate video and audio formats
            video_formats = []
            audio_formats = []
            
            for f in formats:
                if f.get("vcodec") != "none" and f.get("height"):
                    video_formats.append(f)
                elif f.get("vcodec") == "none" and f.get("abr"):
                    audio_formats.append(f)
            
            # Sort video by height descending
            video_formats.sort(key=lambda x: x.get("height", 0), reverse=True)
            # Sort audio by bitrate descending, but prioritize good quality (128kbps+)
            audio_formats.sort(key=lambda x: (x.get("abr", 0) >= 128, x.get("abr", 0)), reverse=True)
            
            seen_video = set()
            for f in video_formats:
                fid = f.get("format_id")
                if not fid or fid in seen_video:
                    continue
                seen_video.add(fid)
                
                height = f.get('height', '?')
                fps = f.get('fps', '')
                vcodec = f.get('vcodec', '').split('.')[0] if f.get('vcodec') else ''
                
                label = f"{height}p"
                if fps and fps > 30:
                    label += f" {fps}fps"
                if vcodec and vcodec != 'avc1':
                    label += f" ({vcodec})"
                
                it = QListWidgetItem(label)
                it.setData(Qt.UserRole, fid)
                video_list.addItem(it)
            
            seen_audio = set()
            for f in audio_formats:
                fid = f.get("format_id")
                if not fid or fid in seen_audio:
                    continue
                seen_audio.add(fid)
                
                abr = f.get('abr', '?')
                acodec = f.get('acodec', '').split('.')[0] if f.get('acodec') else ''
                
                label = f"{abr}kbps"
                if acodec and acodec != 'mp4a':
                    label += f" ({acodec})"
                
                it = QListWidgetItem(label)
                it.setData(Qt.UserRole, fid)
                audio_list.addItem(it)
            
            # Select first items by default
            if video_list.count() > 0:
                video_list.setCurrentRow(0)
            if audio_list.count() > 0:
                # Select a good quality audio, not necessarily the best
                # Look for 128kbps or 160kbps, otherwise pick middle option
                best_row = 0
                for i in range(audio_list.count()):
                    item = audio_list.item(i)
                    label = item.text()
                    if '128kbps' in label or '160kbps' in label:
                        best_row = i
                        break
                # If no preferred found, pick roughly middle quality
                if best_row == 0 and audio_list.count() > 2:
                    best_row = audio_list.count() // 2
                audio_list.setCurrentRow(best_row)
            
            v.addWidget(video_list)
            v.addWidget(audio_list)
            
            # Play button
            btn_layout = QHBoxLayout()
            play_btn = QPushButton("PLAY")
            play_btn.clicked.connect(lambda: self._play_with_formats(url, video_list, audio_list, dlg))
            cancel_btn = QPushButton("CANCEL")
            cancel_btn.clicked.connect(dlg.reject)
            
            btn_layout.addWidget(play_btn)
            btn_layout.addWidget(cancel_btn)
            v.addLayout(btn_layout)
            
            dlg.exec()
        except Exception:
            pass

    def _play_with_formats(self, url, video_list, audio_list, dlg):
        dlg.accept()
        
        video_format = None
        audio_format = None
        
        if video_list.currentItem():
            video_format = video_list.currentItem().data(Qt.UserRole)
        if audio_list.currentItem():
            audio_format = audio_list.currentItem().data(Qt.UserRole)
        
        # Combine formats: video+audio or just video or just audio
        if video_format and audio_format:
            fmt = f"{video_format}+{audio_format}"
        elif video_format:
            fmt = video_format
        elif audio_format:
            fmt = audio_format
        else:
            return  # No format selected
        
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