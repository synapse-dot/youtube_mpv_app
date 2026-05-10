import subprocess
import sys
import argparse
import locale

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QLabel,
    QDialog, QFrame, QMessageBox, QComboBox
)

from app.storage import StorageManager
from app.widgets import SearchResultItem, LoadingSpinner
from app.workers import WorkerSignals, YTSearchWorker, FormatsWorker
from app.themes import Themes


class MainWindow(QWidget):
    MPV_FAST_FLAGS = [
        "--no-terminal",
        "--msg-level=all=no",
        "--prefetch-playlist=yes",
        "--cache=yes",
    ]
    DEFAULT_LANG = (locale.getdefaultlocale()[0] or "en_US").split("_")[0].lower()

    def __init__(self):
        super().__init__()
        self.storage = StorageManager()
        self.current_theme = Themes.get("DEFAULT")
        self.setWindowTitle("MpvTube")
        self.resize(1200, 800)
        self._build_ui()

    def _build_ui(self):
        if self.layout():
            # Clean up old references to avoid RuntimeError
            attrs = ['sidebar', 'body', 'history_list', 'fav_list', 'results', 
                     'spinner', 'search_in', 'search_btn', 'sort_sel', 'status', 'logo']
            for a in attrs:
                if hasattr(self, a):
                    delattr(self, a)
            
            # Nuke the layout
            old_layout = self.layout()
            dummy = QWidget()
            dummy.setLayout(old_layout)
            # Layout is now reparented and will be cleaned up
            
        t = self.current_theme
        root = QHBoxLayout(self) if t["layout"] == "sidebar-left" else QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Common Logo
        self.logo = QLabel("MpvTube")
        self.logo.setObjectName("logo")

        # Sidebar (Left)
        if t["layout"] == "sidebar-left":
            self.sidebar = QFrame()
            self.sidebar.setFixedWidth(280)
            self.sidebar.setObjectName("sidebar")
            side_v = QVBoxLayout(self.sidebar)
            side_v.setContentsMargins(20, 30, 20, 30)
            
            self.logo.setText("MpvTube")
            side_v.addWidget(self.logo)

            side_v.addWidget(QLabel("Recent searches"))
            self.history_list = QListWidget()
            self.history_list.setObjectName("side_list")
            self.history_list.itemClicked.connect(lambda it: self._search_direct(it.text()))
            side_v.addWidget(self.history_list)

            side_v.addWidget(QLabel("Bookmarks"))
            self.fav_list = QListWidget()
            self.fav_list.setObjectName("side_list")
            self.fav_list.itemDoubleClicked.connect(self._play_fav)
            side_v.addWidget(self.fav_list)

            side_v.addStretch()
            root.addWidget(self.sidebar)

        # Body Frame
        self.body = QFrame()
        body_v = QVBoxLayout(self.body)
        
        search_v = QVBoxLayout()
        search_v.setContentsMargins(t["item_padding"], 40, t["item_padding"], 20)
        
        search_h = QHBoxLayout()
        self.search_in = QLineEdit()
        self.search_in.setPlaceholderText("Search YouTube videos")
        self.search_in.returnPressed.connect(self.start_search)
        search_h.addWidget(self.search_in)
        
        self.sort_sel = QComboBox()
        self.sort_sel.addItems(["RELEVANCE", "DATE", "VIEWS", "RATING"])
        search_h.addWidget(self.sort_sel)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.start_search)
        search_h.addWidget(self.search_btn)
        search_v.addLayout(search_h)
        body_v.addLayout(search_v)

        self.results = QListWidget()
        self.results.setObjectName("results")
        self.results.itemActivated.connect(self.play_selected)
        self.results.setSpacing(8)
        body_v.addWidget(self.results)

        footer = QHBoxLayout()
        footer.setContentsMargins(t["item_padding"], 10, t["item_padding"], 10)
        self.status = QLabel("Ready to search")
        footer.addWidget(self.status)
        self.spinner = LoadingSpinner(t)
        footer.addWidget(self.spinner)
        body_v.addLayout(footer)

        root.addWidget(self.body)
        self._apply_styles()
        self._refresh_side()

    def _apply_styles(self):
        t = self.current_theme
        self.setStyleSheet(f"""
            QWidget {{ background: {t['bg']}; color: {t['text']}; font-family: {t['font']}; }}
            QFrame#sidebar {{ background: {t['sidebar_bg']}; border-right: {t['border_width']} solid {t['border_color']}; }}
            QLabel {{ color: {t['text_alt']}; font-size: 10pt; font-weight: 700; letter-spacing: 0.2px; }}
            QLabel#logo {{ color: {t['text']}; font-size: 28pt; font-weight: 900; margin-bottom: 22px; letter-spacing: 0.5px; }}
            QLineEdit {{ background: {t['bg']}; border: {t['border_width']} solid {t['border_color']}; padding: 15px; font-size: 11pt; color: {t['text']}; }}
            QPushButton {{ background: {t['btn_bg']}; color: {t['btn_text']}; border: {t['border_width']} solid {t['border_color']}; padding: 15px 24px; font-weight: 800; }}
            QPushButton:hover {{ background: {t['accent']}; color: {t['bg']}; }}
            QComboBox {{ background: {t['bg']}; border: {t['border_width']} solid {t['border_color']}; padding: 10px; color: {t['text']}; }}
            QListWidget {{ background: transparent; border: none; outline: none; }}
            QListWidget#results::item {{ border-bottom: 1px solid {t['border_color']}; padding: 4px; }}
            QListWidget#side_list {{ font-size: 9pt; color: {t['text']}; }}
            QListWidget#side_list::item:selected {{ color: {t['accent']}; background: transparent; }}
        """)

    def _refresh_side(self):
        if hasattr(self, 'history_list'):
            self.history_list.clear()
            for h in self.storage.data["history"]:
                self.history_list.addItem(h)
        if hasattr(self, 'fav_list'):
            self.fav_list.clear()
            for f in self.storage.data["favorites"]:
                it = QListWidgetItem(f["title"])
                it.setData(Qt.UserRole, f["url"])
                self.fav_list.addItem(it)

    def _search_direct(self, q):
        self.search_in.setText(q)
        self.start_search()

    def _play_fav(self, item):
        self._get_formats(item.data(Qt.UserRole))

    def start_search(self):
        q = self.search_in.text().strip()
        if not q:
            return
        self.results.clear()
        self.storage.add_to_history(q)
        self._refresh_side()
        self.status.setText(f"Searching: {q}")
        self.spinner.start()
        sig = WorkerSignals()
        sig.results.connect(self._populate)
        sig.error.connect(self._on_worker_error)
        sig.finished.connect(self.spinner.stop)
        YTSearchWorker(q, self.storage.get_setting("max_results", 15), sig, self.sort_sel.currentText()).start()

    def _populate(self, entries):
        if not entries:
            self.status.setText("No results found")
            return
        for e in entries:
            it = QListWidgetItem()
            widget = SearchResultItem(e, self.current_theme)
            it.setSizeHint(widget.container.sizeHint())
            url = e.get("webpage_url") or e.get("url")
            if url and not url.startswith("http"):
                url = f"https://youtube.com/watch?v={url}"
            it.setData(Qt.UserRole, url)
            it.setData(Qt.UserRole + 1, e)
            self.results.addItem(it)
            self.results.setItemWidget(it, widget)
        self.status.setText(f"Found {len(entries)} result(s)")

    def play_selected(self, item):
        self._get_formats(item.data(Qt.UserRole))

    def _get_formats(self, url):
        if not url:
            self._show_error("No valid video URL found for this selection.")
            return
        self.status.setText("Loading available formats...")
        self.spinner.start()
        sig = WorkerSignals()
        sig.results.connect(lambda f: self.show_formats(url, f))
        sig.error.connect(self._on_worker_error)
        sig.finished.connect(self.spinner.stop)
        FormatsWorker(url, sig).start()

    def show_formats(self, url, formats):
        dlg = QDialog(self)
        dlg.setWindowTitle("Choose quality")
        dlg.resize(600, 650)
        dlg.setStyleSheet(self.styleSheet())
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Video"))
        vlist = QListWidget()
        v.addWidget(vlist)
        v.addWidget(QLabel("Audio"))
        alist = QListWidget()
        v.addWidget(alist)
        
        v_s = [f for f in formats if f.get("height") and f.get("vcodec") != "none"]
        a_s = [f for f in formats if f.get("abr") and f.get("vcodec") == "none"]
        
        seen_video, seen_audio = set(), set()
        for f in sorted(v_s, key=lambda x: x.get("height", 0), reverse=True):
            label = f"{f.get('height')}p • {f.get('ext')}"
            if label in seen_video:
                continue
            seen_video.add(label)
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, f.get("format_id"))
            vlist.addItem(it)
        for f in sorted(a_s, key=lambda x: x.get("abr", 0), reverse=True):
            label = f"{int(f.get('abr', 0))} kbps"
            if label in seen_audio:
                continue
            seen_audio.add(label)
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, f.get("format_id"))
            alist.addItem(it)
            
        if vlist.count():
            vlist.setCurrentRow(0)
        if alist.count():
            alist.setCurrentRow(0)
            
        row = QHBoxLayout()
        pb = QPushButton("Play")
        pb.clicked.connect(lambda: self._launch(url, vlist, alist, dlg))
        fb = QPushButton("Save bookmark")
        fb.clicked.connect(lambda: self._bookmark(url, dlg))
        row.addWidget(pb)
        row.addWidget(fb)
        v.addLayout(row)
        dlg.exec()

    def _bookmark(self, url, dlg):
        dlg.accept()
        title, thumb = "Unknown video", ""
        for i in range(self.results.count()):
            it = self.results.item(i)
            e = it.data(Qt.UserRole + 1)
            if it.data(Qt.UserRole) == url:
                title = e.get("title", title)
                ts = e.get("thumbnails", [])
                thumb = ts[-1].get("url", "") if ts else ""
                break
        self.storage.add_favorite(title, url, thumb)
        self._refresh_side()

    def _launch(self, url, vlist, alist, dlg):
        dlg.accept()
        vid = vlist.currentItem().data(Qt.UserRole) if vlist.currentItem() else None
        aid = alist.currentItem().data(Qt.UserRole) if alist.currentItem() else None
        fmt = f"{vid}+{aid}" if (vid and aid) else (vid or aid)
        if not fmt:
            self._show_error("No playable format selected.")
            return
        try:
            cmd = [
                self.storage.data["mpv_path"],
                *self.MPV_FAST_FLAGS,
                f"--alang={self.DEFAULT_LANG}",
                f"--slang={self.DEFAULT_LANG}",
                f"--ytdl-format={fmt}",
                url
            ]
            subprocess.Popen(cmd)
            self.status.setText("Playback started in mpv")
            QApplication.instance().quit()
        except FileNotFoundError:
            self._show_error("mpv executable not found. Update your mpv path in config.")
        except Exception as e:
            self._show_error(f"Failed to launch mpv: {e}")

    def _on_worker_error(self, msg):
        self.status.setText("Operation failed")
        self._show_error(msg)

    def _show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MpvTube launcher")
    parser.add_argument("--gui", action="store_true", help="Run graphical interface")
    args = parser.parse_args()

    if args.gui:
        app = QApplication(sys.argv)
        w = MainWindow()
        w.show()
        sys.exit(app.exec())
    else:
        from app.tui import run_tui
        run_tui()
