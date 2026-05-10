import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QLabel,
    QDialog, QFrame, QComboBox, QMessageBox
)

from app.storage import StorageManager
from app.widgets import SearchResultItem, LoadingSpinner
from app.workers import WorkerSignals, YTSearchWorker, FormatsWorker
from app.themes import Themes


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.storage = StorageManager()
        self.current_theme = Themes.get(self.storage.get_setting("theme", "CYBERPUNK"))
        self.setWindowTitle("mpvTube // CORE")
        self.resize(1200, 800)
        self._build_ui()

    def _build_ui(self):
        if self.layout():
            # Clean up old references to avoid RuntimeError
            attrs = ['sidebar', 'body', 'history_list', 'fav_list', 'results', 
                     'spinner', 'search_in', 'search_btn', 'sort_sel', 'status', 'theme_sel', 'logo']
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
        self.logo = QLabel("mpvTube")
        self.logo.setObjectName("logo")

        # Sidebar (Left)
        if t["layout"] == "sidebar-left":
            self.sidebar = QFrame()
            self.sidebar.setFixedWidth(280)
            self.sidebar.setObjectName("sidebar")
            side_v = QVBoxLayout(self.sidebar)
            side_v.setContentsMargins(20, 30, 20, 30)
            
            self.logo.setText("mpvTube // 2.0")
            side_v.addWidget(self.logo)

            side_v.addWidget(QLabel("UPLINKS"))
            self.history_list = QListWidget()
            self.history_list.setObjectName("side_list")
            self.history_list.itemClicked.connect(lambda it: self._search_direct(it.text()))
            side_v.addWidget(self.history_list)

            side_v.addWidget(QLabel("BOOKMARKS"))
            self.fav_list = QListWidget()
            self.fav_list.setObjectName("side_list")
            self.fav_list.itemDoubleClicked.connect(self._play_fav)
            side_v.addWidget(self.fav_list)

            side_v.addStretch()
            side_v.addWidget(QLabel("THEME_ENGINE"))
            self.theme_sel = QComboBox()
            for th in Themes.get_all():
                self.theme_sel.addItem(th["name"])
            self.theme_sel.setCurrentText(t["name"])
            self.theme_sel.currentTextChanged.connect(self._change_theme)
            side_v.addWidget(self.theme_sel)
            
            root.addWidget(self.sidebar)

        # Body Frame
        self.body = QFrame()
        body_v = QVBoxLayout(self.body)
        
        if t["layout"] != "sidebar-left":
            top_nav = QHBoxLayout()
            top_nav.setContentsMargins(t["item_padding"], 20, t["item_padding"], 0)
            
            top_nav.addWidget(self.logo)
            top_nav.addStretch()
            
            self.theme_sel = QComboBox()
            for th in Themes.get_all():
                self.theme_sel.addItem(th["name"])
            self.theme_sel.setCurrentText(t["name"])
            self.theme_sel.currentTextChanged.connect(self._change_theme)
            top_nav.addWidget(self.theme_sel)
            body_v.addLayout(top_nav)

        search_v = QVBoxLayout()
        search_v.setContentsMargins(t["item_padding"], 40, t["item_padding"], 20)
        
        search_h = QHBoxLayout()
        self.search_in = QLineEdit()
        self.search_in.setPlaceholderText("INPUT_QUERY_HERE...")
        self.search_in.returnPressed.connect(self.start_search)
        search_h.addWidget(self.search_in)
        
        self.sort_sel = QComboBox()
        self.sort_sel.addItems(["RELEVANCE", "DATE", "VIEWS", "RATING"])
        search_h.addWidget(self.sort_sel)

        self.search_btn = QPushButton("EXECUTE")
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
        self.status = QLabel("Ready")
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
            QLabel {{ color: {t['accent']}; font-size: 8pt; text-transform: uppercase; font-weight: 900; letter-spacing: 1px; }}
            QLabel#logo {{ color: {t['text'] if t['name'] != 'BRUTALIST' else t['accent']}; font-size: 28pt; font-weight: 900; margin-bottom: 20px; }}
            QLineEdit {{ background: {t['bg']}; border: {t['border_width']} solid {t['border_color']}; padding: 15px; font-size: 11pt; color: {t['text']}; }}
            QPushButton {{ background: {t['btn_bg']}; color: {t['btn_text']}; border: {t['border_width']} solid {t['border_color']}; padding: 15px 30px; font-weight: 900; text-transform: uppercase; }}
            QPushButton:hover {{ background: {t['accent']}; color: {t['bg']}; }}
            QComboBox {{ background: {t['bg']}; border: {t['border_width']} solid {t['border_color']}; padding: 10px; color: {t['text']}; }}
            QListWidget {{ background: transparent; border: none; outline: none; }}
            QListWidget#results::item {{ border-bottom: 1px solid {t['border_color']}; padding: 4px; }}
            QListWidget#side_list {{ font-size: 9pt; color: {t['text']}; }}
            QListWidget#side_list::item:selected {{ color: {t['accent']}; background: transparent; }}
        """)

    def _change_theme(self, name):
        self.storage.set_theme(name)
        self.current_theme = Themes.get(name)
        self._build_ui()

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
        dlg.setWindowTitle("STREAMS")
        dlg.resize(600, 650)
        dlg.setStyleSheet(self.styleSheet())
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("VIDEO"))
        vlist = QListWidget()
        v.addWidget(vlist)
        v.addWidget(QLabel("AUDIO"))
        alist = QListWidget()
        v.addWidget(alist)
        
        v_s = [f for f in formats if f.get("height") and f.get("vcodec") != "none"]
        a_s = [f for f in formats if f.get("abr") and f.get("vcodec") == "none"]
        
        seen_video, seen_audio = set(), set()
        for f in sorted(v_s, key=lambda x: x.get("height", 0), reverse=True):
            label = f"{f.get('height')}P // {f.get('ext')}"
            if label in seen_video:
                continue
            seen_video.add(label)
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, f.get("format_id"))
            vlist.addItem(it)
        for f in sorted(a_s, key=lambda x: x.get("abr", 0), reverse=True):
            label = f"{int(f.get('abr', 0))}KBPS"
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
        pb = QPushButton("PLAY")
        pb.clicked.connect(lambda: self._launch(url, vlist, alist, dlg))
        fb = QPushButton("BOOKMARK")
        fb.clicked.connect(lambda: self._bookmark(url, dlg))
        row.addWidget(pb)
        row.addWidget(fb)
        v.addLayout(row)
        dlg.exec()

    def _bookmark(self, url, dlg):
        dlg.accept()
        title, thumb = "UNKNOWN", ""
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
            subprocess.Popen([self.storage.data["mpv_path"], f"--ytdl-format={fmt}", url])
            self.status.setText("Playback started in mpv")
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
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
