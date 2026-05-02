import subprocess
import sys
import os

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QSpinBox, QListWidget, QListWidgetItem, QLabel,
    QDialog, QMessageBox, QFrame, QComboBox, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QColor

from app.storage import StorageManager
from app.widgets import SearchResultItem, LoadingSpinner
from app.workers import WorkerSignals, YTSearchWorker, FormatsWorker
from app.themes import Themes


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.storage = StorageManager()
        self.current_theme = Themes.get(self.storage.get_setting("theme", "CYBERPUNK"))
        self.setWindowTitle("MPV_TUBE // CORE_INTERFACE")
        self.resize(1200, 800)
        self._build_layout()

    def _build_layout(self):
        # Clear existing
        if self.layout():
            QWidget().setLayout(self.layout())
            
        t = self.current_theme
        root = QHBoxLayout(self) if t["layout"] == "sidebar-left" else QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # UI Components
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        side_v = QVBoxLayout(self.sidebar)
        
        self.logo = QLabel("MPV_TUBE")
        self.logo.setObjectName("logo")
        side_v.addWidget(self.logo)

        self.history_list = QListWidget(); self.history_list.setObjectName("side_list")
        self.history_list.itemClicked.connect(lambda it: self._search_direct(it.text()))
        self.fav_list = QListWidget(); self.fav_list.setObjectName("side_list")
        self.fav_list.itemDoubleClicked.connect(self._play_fav)

        if t["layout"] == "sidebar-left":
            self.sidebar.setFixedWidth(280)
            side_v.addWidget(QLabel("UPLINKS"))
            side_v.addWidget(self.history_list)
            side_v.addWidget(QLabel("BOOKMARKS"))
            side_v.addWidget(self.fav_list)
            
            self.theme_sel = QComboBox()
            for th in Themes.get_all(): self.theme_sel.addItem(th["name"])
            self.theme_sel.setCurrentText(t["name"])
            self.theme_sel.currentTextChanged.connect(self._change_theme)
            side_v.addWidget(QLabel("CONFIG"))
            side_v.addWidget(self.theme_sel)
            
            root.addWidget(self.sidebar)
        
        # Center Area
        self.center = QFrame()
        center_v = QVBoxLayout(self.center)
        padding = 40 if t["name"] == "BRUTALIST" else 20
        center_v.setContentsMargins(padding, padding, padding, padding)

        if t["layout"] == "top-bar":
            top_nav = QHBoxLayout()
            top_nav.addWidget(self.logo)
            self.theme_sel = QComboBox()
            for th in Themes.get_all(): self.theme_sel.addItem(th["name"])
            self.theme_sel.setCurrentText(t["name"])
            self.theme_sel.currentTextChanged.connect(self._change_theme)
            top_nav.addWidget(self.theme_sel)
            center_v.addLayout(top_nav)

        search_bar = QHBoxLayout()
        self.search_in = QLineEdit()
        self.search_in.setPlaceholderText("TYPE_SEARCH_QUERY...")
        self.search_in.returnPressed.connect(self.start_search)
        search_bar.addWidget(self.search_in)
        
        self.search_btn = QPushButton("EXECUTE")
        self.search_btn.clicked.connect(self.start_search)
        search_bar.addWidget(self.search_btn)
        center_v.addLayout(search_bar)

        self.results = QListWidget()
        self.results.setObjectName("results")
        self.results.itemActivated.connect(self.play_selected)
        center_v.addWidget(self.results)

        status_row = QHBoxLayout()
        self.status = QLabel("SYSTEM_READY")
        status_row.addWidget(self.status)
        self.spinner = LoadingSpinner(t)
        status_row.addWidget(self.spinner)
        center_v.addLayout(status_row)

        root.addWidget(self.center)
        self._apply_styles()
        self._refresh_side()

    def _apply_styles(self):
        t = self.current_theme
        self.setStyleSheet(f"""
            QWidget {{
                background: {t['bg']};
                color: {t['text']};
                font-family: {t['font']};
            }}
            QFrame#sidebar {{
                background: {t['sidebar_bg']};
                border-right: {t['border']};
            }}
            QLabel {{
                color: {t['accent']};
                font-size: 8pt;
                text-transform: uppercase;
                font-weight: bold;
            }}
            QLabel#logo {{
                color: {t['text'] if t['name'] != 'BRUTALIST' else t['accent']};
                font-size: 24pt;
                font-weight: 900;
                margin-bottom: 20px;
            }}
            QLineEdit {{
                background: {t['bg']};
                border: {t['border']};
                padding: 15px;
                font-size: 12pt;
            }}
            QPushButton {{
                background: {t['accent']};
                color: {t['bg'] if t['name'] != 'VOGUE' else t['text']};
                border: {t['border']};
                padding: 15px 30px;
                font-weight: 900;
                text-transform: uppercase;
            }}
            QListWidget {{
                background: transparent;
                border: none;
            }}
            QComboBox {{
                background: {t['bg']};
                border: {t['border']};
                padding: 10px;
            }}
        """)

    def _change_theme(self, name):
        self.storage.set_theme(name)
        self.current_theme = Themes.get(name)
        self._build_layout()

    def _refresh_side(self):
        self.history_list.clear()
        for h in self.storage.data["history"]: self.history_list.addItem(h)
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
        if not q: return
        self.results.clear()
        self.storage.add_to_history(q)
        self._refresh_side()
        self.spinner.start()
        sig = WorkerSignals()
        sig.results.connect(self._populate)
        sig.finished.connect(self.spinner.stop)
        YTSearchWorker(q, self.storage.get_setting("max_results", 15), sig).start()

    def _populate(self, entries):
        for e in entries:
            it = QListWidgetItem()
            widget = SearchResultItem(e, self.current_theme)
            it.setSizeHint(widget.sizeHint())
            url = e.get("webpage_url") or e.get("url")
            if url and not url.startswith("http"): url = f"https://youtube.com/watch?v={url}"
            it.setData(Qt.UserRole, url)
            it.setData(Qt.UserRole+1, e)
            self.results.addItem(it)
            self.results.setItemWidget(it, widget)
            it.setSizeHint(widget.container.sizeHint())

    def play_selected(self, item): self._get_formats(item.data(Qt.UserRole))

    def _get_formats(self, url):
        self.spinner.start()
        sig = WorkerSignals()
        sig.results.connect(lambda f: self.show_formats(url, f))
        sig.finished.connect(self.spinner.stop)
        FormatsWorker(url, sig).start()

    def show_formats(self, url, formats):
        dlg = QDialog(self)
        dlg.setWindowTitle("SELECT_STREAM")
        dlg.resize(600, 600)
        dlg.setStyleSheet(self.styleSheet())
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("VIDEO"))
        vlist = QListWidget(); v.addWidget(vlist)
        v.addWidget(QLabel("AUDIO"))
        alist = QListWidget(); v.addWidget(alist)
        
        v_s = [f for f in formats if f.get("height") and f.get("vcodec") != "none"]
        a_s = [f for f in formats if f.get("abr") and f.get("vcodec") == "none"]

        for f in sorted(v_s, key=lambda x: x.get("height", 0), reverse=True):
            it = QListWidgetItem(f"{f.get('height')}P // {f.get('ext')}"); it.setData(Qt.UserRole, f.get("format_id")); vlist.addItem(it)
        for f in sorted(a_s, key=lambda x: x.get("abr", 0), reverse=True):
            it = QListWidgetItem(f"{int(f.get('abr'))}KBPS"); it.setData(Qt.UserRole, f.get("format_id")); alist.addItem(it)

        if vlist.count(): vlist.setCurrentRow(0)
        if alist.count(): alist.setCurrentRow(0)

        row = QHBoxLayout()
        pb = QPushButton("PLAY"); pb.clicked.connect(lambda: self._launch(url, vlist, alist, dlg))
        fb = QPushButton("BOOKMARK"); fb.clicked.connect(lambda: self._bookmark(url, dlg))
        row.addWidget(pb); row.addWidget(fb); v.addLayout(row)
        dlg.exec()

    def _bookmark(self, url, dlg):
        dlg.accept()
        title, thumb = "UNKNOWN", ""
        for i in range(self.results.count()):
            it = self.results.item(i); e = it.data(Qt.UserRole+1)
            if it.data(Qt.UserRole) == url: title = e.get("title", title); ts = e.get("thumbnails", []); thumb = ts[-1].get("url", "") if ts else ""; break
        self.storage.add_favorite(title, url, thumb); self._refresh_side()

    def _launch(self, url, vlist, alist, dlg):
        dlg.accept()
        vid = vlist.currentItem().data(Qt.UserRole) if vlist.currentItem() else None
        aid = alist.currentItem().data(Qt.UserRole) if alist.currentItem() else None
        fmt = f"{vid}+{aid}" if (vid and aid) else (vid or aid)
        subprocess.Popen([self.storage.data["mpv_path"], f"--ytdl-format={fmt}", url])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow(); w.show(); sys.exit(app.exec())
