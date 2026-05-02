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
        title.setObjectName("app_title")
        subtitle = QLabel("Editorial dark UI • fast search • precise playback")
        subtitle.setObjectName("subtitle")
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
        v.addWidget(self.status)

    def _style(self):
        self.setStyleSheet("""
            QWidget {background:#0e1015; color:#ece7de; font-family:'IBM Plex Sans','Source Sans Pro','Noto Sans'; font-size:10.5pt;}
            QLabel#app_title {font-family:'Bodoni MT','Playfair Display','Times New Roman'; font-size:30pt; letter-spacing:1px; color:#f5efe5;}
            QLabel#subtitle {color:#a9a29a; margin-bottom:6px;}
            QLineEdit,QSpinBox {background:#181c24; border:1px solid #31384a; border-radius:10px; padding:10px 12px; color:#f0ece4;}
            QLineEdit:focus,QSpinBox:focus {border:1px solid #d8b26e;}
            QPushButton {background:#d8b26e; color:#121212; border:1px solid #f0c57a; border-radius:10px; padding:10px 16px; font-weight:700; letter-spacing:0.4px;}
            QPushButton:hover {background:#e8bf78;}
            QPushButton:pressed {background:#c39d5f;}
            QPushButton:disabled {background:#3e3a33; color:#9c968d; border:1px solid #524d45;}
            QListWidget {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #121721, stop:1 #17131f); border:1px solid #2a3142; border-radius:12px;}
            QListWidget::item {padding:8px; margin:3px;}
            QListWidget::item:hover {background:#2b3346;}
            QListWidget::item:selected {background:#d8b26e; color:#171717;}
            QLabel#result_title {font-weight:650; font-size:11.2pt; color:#f6f1e9;}
            QLabel#result_meta {color:#b4aea4; font-size:9.2pt;}
            QLabel#status_label {color:#a5abbe; font-size:9pt; padding:2px 2px 0 2px;}
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

        sig = WorkerSignals()
        sig.results.connect(self._populate)
        sig.error.connect(self._show_search_error)
        sig.finished.connect(self._search_finished)
        YTSearchWorker(query, self.count.value(), sig).start()

    def _show_search_error(self, text):
        self.status.setText("Search failed.")
        QMessageBox.critical(self, "Search Error", f"Could not complete search.\n\n{text}")

    def _search_finished(self):
        self.search.setEnabled(True)
        self.count.setEnabled(True)
        self.search_btn.setEnabled(True)
        self.search_btn.setText("SEARCH")
        if self.results.count() == 0 and self.status.text() not in {"Search failed.", "No results found. Try another query."}:
            self.status.setText("Ready")

    def _resolve_entry_url(self, entry):
        url = entry.get("webpage_url") or entry.get("url")
        if not url:
            return None
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"https://www.youtube.com/watch?v={url}"

    def _populate(self, entries):
        if not entries:
            self.status.setText("No results found. Try another query.")
            return
        added = 0
        for e in entries:
            item = QListWidgetItem()
            item.setSizeHint(QSize(450, 108))
            item.setData(Qt.UserRole, self._resolve_entry_url(e))
            self.results.addItem(item)
            self.results.setItemWidget(item, SearchResultItem(e))
            added += 1
        self.status.setText(f"Showing {added} result(s). Double-click a row to pick quality.")

    def play_selected(self, item):
        url = item.data(Qt.UserRole)
        if not url:
            QMessageBox.warning(self, "Invalid Selection", "This result has no playable URL.")
            return
        self.status.setText("Loading available qualities...")

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
        v = video_list.currentItem().data(Qt.UserRole) if video_list.currentItem() else None
        a = audio_list.currentItem().data(Qt.UserRole) if audio_list.currentItem() else None
        if not v and not a:
            return
        fmt = f"{v}+{a}" if v and a else (v or a)
        self.status.setText("Opening mpv...")
        try:
            subprocess.run([self.storage.data["mpv_path"], f"--ytdl-format={fmt}", url], check=True)
        except FileNotFoundError:
            QMessageBox.critical(self, "mpv Not Found", "mpv was not found. Install mpv or set mpv_path in ~/.youtube_mpv_config.json.")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "mpv Error", f"mpv exited with code {e.returncode}.")
        finally:
            self.status.setText("Ready")


def main():
    app = QApplication([])
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
