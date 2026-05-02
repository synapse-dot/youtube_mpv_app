import subprocess
import sys

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QObject, QSize
from PySide6.QtGui import QPainter, QColor, QPixmap


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
        blank.fill(QColor("#313244"))  # Catppuccin surface0
        self.thumb.setPixmap(blank)
        self.thumb.setStyleSheet("""
            background: #313244;
            border: 2px solid #45475a;
            border-radius: 6px;
        """)
        root.addWidget(self.thumb)

        text = QVBoxLayout()
        title = QLabel(entry.get("title", "Unknown"))
        title.setStyleSheet("""
            color: #cdd6f4;
            font-weight: 600;
            font-size: 11pt;
        """)
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
        meta_lbl.setStyleSheet("""
            color: #a6adc8;
            font-size: 9pt;
        """)
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

from app.storage import StorageManager
from app.widgets import SearchResultItem
from app.workers import WorkerSignals, YTSearchWorker, FormatsWorker


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.storage = StorageManager()

        self.setWindowTitle("mpvTube")
        self.resize(1120, 820)
        self._style()

        v = QVBoxLayout(self)
        v.setSpacing(12)

        title = QLabel("mpvTube")
        title.setStyleSheet("""
            color: #89b4fa;
            font-size: 24pt;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        v.addWidget(title)
        v.addWidget(subtitle)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search YouTube or paste a video URL")
        self.search.returnPressed.connect(self.start_search)
        bar.addWidget(self.search)

        self.count = QSpinBox()
        self.count.setRange(1, 50)
        self.count.setValue(self.storage.get_setting("max_results", 10))
        bar.addWidget(self.count)

        self.search_btn = QPushButton("SEARCH")
        self.search_btn.clicked.connect(self.start_search)
        bar.addWidget(self.search_btn)

        v.addLayout(bar)

        self.results = QListWidget()
        self.results.itemActivated.connect(self.play_selected)
        v.addWidget(self.results)

        self.status = QLabel("Ready")
        self.status.setObjectName("status_label")
        self.status.setAlignment(Qt.AlignLeft)
        v.addWidget(self.status)

    def _style(self):
        self.setStyleSheet("""
            QWidget {
                background: #181a20;
                color: #cdd6f4;
                font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
                font-size: 10pt;
            }
            
            QLabel {
                color: #cdd6f4;
            }
            
            QLineEdit, QSpinBox {
                background: #313244;
                border: 2px solid #45475a;
                border-radius: 8px;
                padding: 8px 12px;
                color: #cdd6f4;
                selection-background-color: #89b4fa;
            }
            
            QLineEdit:focus, QSpinBox:focus {
                border-color: #89b4fa;
                background: #45475a;
            }
            
            QPushButton {
                background: #7aa2f7;
                border: 1px solid #86acef;
                border-radius: 8px;
                padding: 8px 16px;
                color: #111319;
                font-weight: 600;
            }
            
            QPushButton:hover {
                background: #8eb0f8;
            }
            
            QPushButton:pressed {
                background: #6898ef;
            }

            QPushButton:disabled {
                background: #45475a;
                border: 1px solid #5c5f77;
                color: #8f94b0;
            }
            
            QListWidget {
                background: #12131a;
                border: 1px solid #313244;
                border-radius: 8px;
                alternate-background-color: #313244;
            }
            
            QListWidget::item {
                padding: 6px;
                border-radius: 6px;
                margin: 2px;
            }
            
            QListWidget::item:selected {
                background: #7aa2f7;
                color: #111319;
            }
            
            QListWidget::item:hover {
                background: #3a3d52;
            }

            QLabel#status_label {
                color: #9aa0bf;
                font-size: 9pt;
                padding: 4px 2px 0 2px;
            }
            
            QDialog QPushButton {
                background: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                min-width: 80px;
            }
            
            QDialog QPushButton:hover {
                background: #94e2d5;
            }
            
            QDialog QPushButton#cancel_btn {
                background: #f38ba8;
            }
            
            QDialog QPushButton#cancel_btn:hover {
                background: #eba0ac;
            }
        """)

    def start_search(self):
        query = self.search.text().strip()
        if not query:
            return

        self.results.clear()
        self.storage.add_to_history(query)
        self.search.setEnabled(False)
        self.count.setEnabled(False)
        self.search_btn.setEnabled(False)
        self.search_btn.setText("SEARCHING...")
        self.status.setText(f"Searching for: {query}")

        self.search_btn.setEnabled(False)
        self.search_btn.setText("SEARCHING...")

        sig = WorkerSignals()
        sig.results.connect(self._populate)
        sig.error.connect(lambda e: QMessageBox.critical(self, "Search Error", f"Could not complete search.\n\n{e}"))
        sig.finished.connect(self._search_finished)

        YTSearchWorker(q, self.count.value(), sig).start()


    def _search_finished(self):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("SEARCH")

    def _resolve_entry_url(self, entry):
        url = entry.get("webpage_url") or entry.get("url")
        if not url:
            return None
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"https://www.youtube.com/watch?v={url}"

    def _populate(self, entries):
        try:
            if not entries:
                self.status.setText("No results found. Try another query.")
                return

            added = 0
            for e in entries:
                item = QListWidgetItem()
                widget = SearchResultItem(e)
                item.setSizeHint(QSize(400, 100))
                item.setData(Qt.UserRole, self._resolve_entry_url(e))
                self.results.addItem(item)
                self.results.setItemWidget(item, widget)
                added += 1
            self.status.setText(f"Showing {added} result(s). Double-click to pick quality.")
        except Exception:
            self.status.setText("UI refreshed during search.")

    def play_selected(self, item):
        url = item.data(Qt.UserRole)
        if not url:
            QMessageBox.warning(self, "Invalid Selection", "This result has no playable URL.")
            return

        sig = WorkerSignals()
        sig.results.connect(lambda f: self.show_formats_dialog(url, f))
        sig.error.connect(lambda e: QMessageBox.critical(self, "Error", e))

        sig.finished.connect(lambda: self.status.setText("Ready"))
        FormatsWorker(url, sig).start()

    def show_formats_dialog(self, url, formats):
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Quality")
        dlg.resize(700, 500)
        dlg.setStyleSheet(self.styleSheet())
        v = QVBoxLayout(dlg)

        v.addWidget(QLabel("Video Quality"))
        video_list = QListWidget(); video_list.setMaximumHeight(220)
        v.addWidget(video_list)
        v.addWidget(QLabel("Audio Quality"))
        audio_list = QListWidget(); audio_list.setMaximumHeight(160)
        v.addWidget(audio_list)

        for f in sorted([x for x in formats if x.get("height") and x.get("vcodec") != "none"], key=lambda x: x.get("height", 0), reverse=True):
            it = QListWidgetItem(f"{f.get('height','?')}p")
            it.setData(Qt.UserRole, f.get("format_id"))
            video_list.addItem(it)
        for f in sorted([x for x in formats if x.get("abr") and x.get("vcodec") == "none"], key=lambda x: x.get("abr", 0), reverse=True):
            it = QListWidgetItem(f"{int(f.get('abr', 0))}kbps")
            it.setData(Qt.UserRole, f.get("format_id"))
            audio_list.addItem(it)

        if video_list.count() > 0: video_list.setCurrentRow(0)
        if audio_list.count() > 0: audio_list.setCurrentRow(0)

        row = QHBoxLayout()
        play = QPushButton("PLAY")
        play.clicked.connect(lambda: self._play_with_formats(url, video_list, audio_list, dlg))
        cancel = QPushButton("CANCEL")
        cancel.clicked.connect(dlg.reject)
        row.addWidget(play); row.addWidget(cancel); v.addLayout(row)
        dlg.exec()

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
        
        try:
            subprocess.run(
                [self.storage.data["mpv_path"], f"--ytdl-format={fmt}", url],
                check=True
            )
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "mpv Not Found",
                "mpv was not found. Install mpv or set the correct mpv path in ~/.youtube_mpv_config.json."
            )
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "mpv Error", f"mpv exited with code {e.returncode}.")


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
