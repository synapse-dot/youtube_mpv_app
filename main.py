import sys
import os
import json
import shutil
import webbrowser
import subprocess
import threading
from functools import partial
import urllib.request
import zipfile
import tempfile
from datetime import datetime
import time

from yt_dlp import YoutubeDL
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
    QComboBox,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QRect
from PySide6.QtGui import QKeySequence, QFont, QPainter, QColor, QPixmap
from PySide6.QtWidgets import QCheckBox


class StorageManager:
    """Manages persistent storage for history, favorites, and settings."""
    def __init__(self):
        self.config_path = os.path.join(os.path.expanduser("~"), ".youtube_mpv_config.json")
        self.data = self._load()

    def _load(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "mpv_path": os.environ.get("MPV_PATH", "mpv"),
            "history": [],
            "favorites": [],
            "settings": {
                "default_quality": "best",
                "auto_start_last": False,
                "max_results": 10,
            }
        }

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    def add_to_history(self, query):
        if query not in self.data.get("history", []):
            self.data.setdefault("history", []).insert(0, query)
            self.data["history"] = self.data["history"][:20]  # Keep last 20
            self.save()

    def add_favorite(self, video_data):
        favorites = self.data.setdefault("favorites", [])
        if video_data not in favorites:
            favorites.insert(0, video_data)
            self.data["favorites"] = favorites[:50]  # Keep last 50
            self.save()

    def remove_favorite(self, url):
        favorites = self.data.get("favorites", [])
        self.data["favorites"] = [f for f in favorites if f.get("url") != url]
        self.save()

    def get_setting(self, key, default=None):
        return self.data.get("settings", {}).get(key, default)

    def set_setting(self, key, value):
        self.data.setdefault("settings", {})[key] = value
        self.save()


class LoadingSpinner(QWidget):
    """Animated loading spinner."""
    def __init__(self):
        super().__init__()
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.rotate)
        self.setFixedSize(24, 24)

    def start(self):
        self.angle = 0
        self.timer.start(30)

    def stop(self):
        self.timer.stop()

    def rotate(self):
        self.angle = (self.angle + 12) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(12, 12)
        painter.rotate(self.angle)

        for i in range(12):
            alpha = int(255 * (1 - i / 12))
            color = QColor(45, 140, 255, alpha)
            painter.fillRect(QRect(-2, -8, 4, 4), color)
            painter.rotate(30)


class WorkerSignals(QObject):
    results = Signal(object)
    error = Signal(str)
    finished = Signal()
    progress = Signal(str)


class YTSearchWorker(threading.Thread):
    def __init__(self, query, signals, max_results=10):
        super().__init__()
        self.query = query
        self.signals = signals
        self.max_results = max_results
        self.daemon = True
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        ydl_opts = {"extract_flat": True, "skip_download": True}
        try:
            with YoutubeDL(ydl_opts) as ydl:
                n = max(1, int(self.max_results))
                search_term = f"ytsearch{n}:{self.query}"
                info = ydl.extract_info(search_term, download=False)
                entries = info.get("entries", [])
                
                if not self._stop_event.is_set():
                    self.signals.results.emit(entries)
        except Exception as e:
            if not self._stop_event.is_set():
                self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class FormatsWorker(threading.Thread):
    def __init__(self, url, signals):
        super().__init__()
        self.url = url
        self.signals = signals
        self.daemon = True
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        ydl_opts = {"skip_download": True}
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                formats = info.get("formats", [])
                if not self._stop_event.is_set():
                    self.signals.results.emit(formats)
        except Exception as e:
            if not self._stop_event.is_set():
                self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class SearchResultItem(QWidget):
    """Custom widget for enhanced search result display."""
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.entry = entry
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Title
        title = QLabel(entry.get("title", "Unknown"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title.setFont(title_font)
        title.setWordWrap(True)
        layout.addWidget(title)

        # Duration and date
        info_layout = QHBoxLayout()
        duration = entry.get("duration")
        upload_date = entry.get("upload_date")
        
        info_text = ""
        if duration:
            mins, secs = divmod(duration, 60)
            info_text += f"⏱ {int(mins)}:{int(secs):02d}"
        if upload_date:
            try:
                date_obj = datetime.strptime(str(upload_date), "%Y%m%d")
                info_text += f" • 📅 {date_obj.strftime('%b %d, %Y')}"
            except:
                pass

        if info_text:
            info_label = QLabel(info_text)
            info_label.setStyleSheet("color: #666; font-size: 9pt;")
            info_layout.addWidget(info_label)

        # Copy URL button
        copy_btn = QPushButton("📋 Copy URL")
        copy_btn.setMaximumWidth(100)
        copy_btn.setStyleSheet(
            "QPushButton { padding: 4px 8px; border-radius: 4px; background-color: #e8e8e8; border: none; font-size: 8pt; }"
            "QPushButton:hover { background-color: #d8d8d8; }"
        )
        copy_btn.clicked.connect(lambda: self.copy_url())
        info_layout.addWidget(copy_btn)
        info_layout.addStretch()
        layout.addLayout(info_layout)

    def copy_url(self):
        from PySide6.QtGui import QClipboard
        from PySide6.QtWidgets import QApplication
        url = self.entry.get("webpage_url") or self.entry.get("url")
        if url:
            QApplication.clipboard().setText(url)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.storage = StorageManager()
        self.search_worker = None
        self.formats_worker = None
        
        self.setWindowTitle("mpvTube — YouTube to mpv")
        self.resize(1000, 800)
        self.setMinimumSize(800, 600)

        # Modern gorgeous stylesheet
        self.apply_stylesheet()

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(12)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # Header
        self.create_header()
        
        # Top bar with mpv path and settings
        self.create_topbar()
        
        # ffmpeg warning
        self.create_ffmpeg_warning()
        
        # Search bar with history
        self.create_searchbar()
        
        # Status and spinner
        self.create_status_bar()
        
        # Favorites section
        self.create_favorites_section()
        
        # Results with sorting
        self.create_results_section()

    def apply_stylesheet(self):
        """Apply a beautiful, modern stylesheet."""
        stylesheet = """
            QWidget { background-color: #f8f9fa; }
            
            QLabel#appTitle {
                font-size: 24pt;
                font-weight: 700;
                color: #1a1a2e;
                margin: 0px;
            }
            
            QLabel#appSubtitle {
                color: #6c757d;
                font-size: 11pt;
                margin: 4px 0px 0px 0px;
            }
            
            QLabel#statusLabel {
                color: #495057;
                font-size: 10pt;
                font-weight: 500;
            }
            
            QPushButton#primary {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2d8cff, stop:1 #1a6dd6);
                color: white;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: 600;
                border: none;
                font-size: 10pt;
            }
            
            QPushButton#primary:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3498db, stop:1 #2980b9);
            }
            
            QPushButton#primary:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a6dd6, stop:1 #0f4a99);
            }
            
            QPushButton#secondary {
                background-color: #e8e8e8;
                color: #333;
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid #d0d0d0;
                font-weight: 500;
            }
            
            QPushButton#secondary:hover {
                background-color: #d8d8d8;
            }
            
            QPushButton#danger {
                background-color: #ff6b6b;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                border: none;
                font-weight: 500;
            }
            
            QPushButton#danger:hover {
                background-color: #ee5a52;
            }
            
            QLineEdit {
                padding: 10px 12px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
                font-size: 10pt;
                selection-background-color: #2d8cff;
            }
            
            QLineEdit:focus {
                border: 2px solid #2d8cff;
                background-color: #ffffff;
            }
            
            QSpinBox {
                padding: 8px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
            }
            
            QSpinBox:focus {
                border: 2px solid #2d8cff;
            }
            
            QComboBox {
                padding: 8px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
                selection-background-color: #2d8cff;
            }
            
            QComboBox:focus {
                border: 2px solid #2d8cff;
            }
            
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            
            QComboBox::down-arrow {
                image: none;
                width: 12px;
                height: 12px;
            }
            
            QListWidget {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                outline: none;
            }
            
            QListWidget::item {
                padding: 6px;
                border-radius: 4px;
            }
            
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
            
            QListWidget::item:selected {
                background-color: #2d8cff;
                color: white;
            }
            
            QDialog {
                background-color: #f8f9fa;
            }
            
            QCheckBox {
                color: #333;
                spacing: 6px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #d0d0d0;
                background-color: white;
            }
            
            QCheckBox::indicator:checked {
                background-color: #2d8cff;
                border: 2px solid #2d8cff;
            }
        """
        self.setStyleSheet(stylesheet)

    def create_header(self):
        """Create app header with title and subtitle."""
        header = QVBoxLayout()
        header.setSpacing(2)
        
        title = QLabel("🎬 mpvTube")
        title.setObjectName("appTitle")
        
        subtitle = QLabel("Search YouTube and play in mpv • Beautiful & Fast")
        subtitle.setObjectName("appSubtitle")
        
        header.addWidget(title)
        header.addWidget(subtitle)
        self.layout.addLayout(header)

    def create_topbar(self):
        """Create top bar with mpv path, test, and settings."""
        topbar = QHBoxLayout()
        topbar.setSpacing(10)
        
        topbar.addWidget(QLabel("mpv path:"))
        self.mpv_path_input = QLineEdit(self.storage.data.get("mpv_path", "mpv"))
        self.mpv_path_input.setMaximumWidth(250)
        self.mpv_path_input.setToolTip("Path to mpv executable")
        topbar.addWidget(self.mpv_path_input)
        
        self.test_mpv_btn = QPushButton("🧪 Test")
        self.test_mpv_btn.clicked.connect(self.test_mpv)
        self.test_mpv_btn.setObjectName("secondary")
        self.test_mpv_btn.setMaximumWidth(80)
        topbar.addWidget(self.test_mpv_btn)
        
        self.play_best_btn = QPushButton("▶ Play Best")
        self.play_best_btn.clicked.connect(self.play_best_for_selection)
        self.play_best_btn.setObjectName("primary")
        self.play_best_btn.setMaximumWidth(110)
        topbar.addWidget(self.play_best_btn)
        
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(self.open_settings)
        settings_btn.setObjectName("secondary")
        settings_btn.setMaximumWidth(100)
        topbar.addWidget(settings_btn)
        
        topbar.addStretch()
        self.layout.addLayout(topbar)

    def create_ffmpeg_warning(self):
        """Create ffmpeg warning if not found."""
        if not shutil.which("ffmpeg"):
            warn_layout = QHBoxLayout()
            warn_label = QLabel("⚠️  ffmpeg not found. Install ffmpeg for better audio/video handling.")
            warn_label.setStyleSheet("color: #c92a2a; font-weight: 500;")
            warn_layout.addWidget(warn_label)
            
            install_btn = QPushButton("Install ffmpeg")
            install_btn.clicked.connect(self.install_ffmpeg)
            install_btn.setObjectName("secondary")
            install_btn.setMaximumWidth(140)
            warn_layout.addWidget(install_btn)
            warn_layout.addStretch()
            self.layout.addLayout(warn_layout)

    def create_searchbar(self):
        """Create search bar with history dropdown."""
        searchbar = QHBoxLayout()
        searchbar.setSpacing(10)
        
        # History dropdown
        self.history_combo = QComboBox()
        self.history_combo.addItem("📋 Recent Searches...")
        self.history_combo.addItems(self.storage.data.get("history", []))
        self.history_combo.setMaximumWidth(200)
        self.history_combo.currentTextChanged.connect(self.on_history_selected)
        searchbar.addWidget(self.history_combo)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search YouTube or paste URL...")
        self.search_input.returnPressed.connect(self.start_search)
        searchbar.addWidget(self.search_input)
        
        # Results count
        searchbar.addWidget(QLabel("Results:"))
        self.search_count_spin = QSpinBox()
        self.search_count_spin.setRange(1, 50)
        self.search_count_spin.setValue(self.storage.get_setting("max_results", 10))
        self.search_count_spin.setMaximumWidth(70)
        searchbar.addWidget(self.search_count_spin)
        
        # Search button
        self.search_btn = QPushButton("🔍 Search")
        self.search_btn.setObjectName("primary")
        self.search_btn.clicked.connect(self.start_search)
        self.search_btn.setMaximumWidth(100)
        searchbar.addWidget(self.search_btn)
        
        # Cancel button (initially hidden)
        self.cancel_search_btn = QPushButton("⏹ Cancel")
        self.cancel_search_btn.setObjectName("danger")
        self.cancel_search_btn.clicked.connect(self.cancel_search)
        self.cancel_search_btn.setMaximumWidth(100)
        self.cancel_search_btn.hide()
        searchbar.addWidget(self.cancel_search_btn)
        
        self.layout.addLayout(searchbar)

    def create_status_bar(self):
        """Create status bar with spinner and progress."""
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)
        
        self.spinner = LoadingSpinner()
        self.spinner.hide()
        status_layout.addWidget(self.spinner)
        
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.layout.addLayout(status_layout)

    def create_favorites_section(self):
        """Create favorites quick-access section."""
        fav_layout = QHBoxLayout()
        fav_layout.setSpacing(8)
        
        fav_label = QLabel("⭐ Favorites:")
        fav_label.setStyleSheet("font-weight: 600; color: #333;")
        fav_layout.addWidget(fav_label)
        
        self.favorites_list = QListWidget()
        self.favorites_list.setMaximumHeight(80)
        self.favorites_list.itemActivated.connect(self.play_favorite)
        
        for fav in self.storage.data.get("favorites", []):
            item = QListWidgetItem(fav.get("title", "Unknown"))
            item.setData(Qt.UserRole, fav.get("url"))
            self.favorites_list.addItem(item)
        
        fav_layout.addWidget(self.favorites_list)
        self.layout.addLayout(fav_layout)

    def create_results_section(self):
        """Create results list with sorting options."""
        results_header = QHBoxLayout()
        results_header.setSpacing(10)
        
        results_label = QLabel("Search Results:")
        results_label.setStyleSheet("font-weight: 600; font-size: 11pt; color: #333;")
        results_header.addWidget(results_label)
        
        # Sort dropdown
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Relevance", "Duration (Short)", "Duration (Long)", "Newest", "Oldest"])
        self.sort_combo.setMaximumWidth(150)
        self.sort_combo.currentTextChanged.connect(self.apply_sort)
        results_header.addWidget(self.sort_combo)
        
        results_header.addStretch()
        self.layout.addLayout(results_header)
        
        self.results_list = QListWidget()
        self.results_list.itemActivated.connect(self.open_formats_dialog)
        self.results_list.setToolTip("Double-click to select quality")
        self.layout.addWidget(self.results_list)
        
        self.results_data = []  # Store full entry data

    def on_history_selected(self, text):
        """Handle history selection."""
        if text and text != "📋 Recent Searches...":
            self.search_input.setText(text)
            self.start_search()

    def apply_sort(self, sort_type):
        """Apply sorting to results."""
        if not self.results_data:
            return

        sorted_data = self.results_data.copy()
        
        if sort_type == "Duration (Short)":
            sorted_data.sort(key=lambda x: x.get("duration", 0) or 0)
        elif sort_type == "Duration (Long)":
            sorted_data.sort(key=lambda x: x.get("duration", 0) or 0, reverse=True)
        elif sort_type == "Newest":
            sorted_data.sort(key=lambda x: x.get("upload_date", "0"), reverse=True)
        elif sort_type == "Oldest":
            sorted_data.sort(key=lambda x: x.get("upload_date", "0"))

        self.update_results_list(sorted_data)

    def update_results_list(self, entries):
        """Update results list with entries."""
        self.results_list.clear()
        for entry in entries:
            item = QListWidgetItem()
            widget = SearchResultItem(entry)
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, entry.get("webpage_url") or entry.get("url"))
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)

    def start_search(self):
        """Start YouTube search."""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Empty Search", "Please enter a search term or URL.")
            return
        
        self.storage.add_to_history(query)
        self.status_label.setText("🔍 Searching...")
        self.spinner.start()
        self.spinner.show()
        self.search_btn.hide()
        self.cancel_search_btn.show()
        self.search_btn.setEnabled(False)
        self.results_list.clear()
        self.results_data = []

        self.signals = WorkerSignals()
        self.signals.results.connect(self.on_search_results)
        self.signals.error.connect(self.on_error)
        self.signals.finished.connect(self.on_search_finished)

        self.search_worker = YTSearchWorker(
            query, self.signals, 
            max_results=self.search_count_spin.value()
        )
        self.search_worker.start()

    def cancel_search(self):
        """Cancel ongoing search."""
        if self.search_worker:
            self.search_worker.stop()
        self.on_search_finished()
        self.status_label.setText("Search cancelled")

    def on_search_results(self, entries):
        """Handle search results."""
        if entries:
            self.results_data = entries
            self.status_label.setText(f"✓ Found {len(entries)} result{'s' if len(entries) != 1 else ''}")
            self.update_results_list(entries)
        else:
            self.status_label.setText("No results found")

    def on_search_finished(self):
        """Called when search finishes."""
        self.spinner.stop()
        self.spinner.hide()
        self.search_btn.show()
        self.cancel_search_btn.hide()
        self.search_btn.setEnabled(True)

    def on_error(self, msg):
        """Handle errors."""
        self.on_search_finished()
        self.status_label.setText("⚠️ Error during search")
        QMessageBox.critical(self, "Search Error", f"An error occurred:\n\n{msg}")

    def open_formats_dialog(self, item: QListWidgetItem):
        """Open format selection dialog."""
        url = item.data(Qt.UserRole)
        self.status_label.setText("⏳ Loading formats...")
        self.spinner.start()
        self.spinner.show()
        self.results_list.setEnabled(False)

        self.formats_signals = WorkerSignals()
        self.formats_signals.results.connect(partial(self.show_formats_dialog, url))
        self.formats_signals.error.connect(self.on_error_formats)
        self.formats_signals.finished.connect(lambda: self.spinner.stop())

        self.formats_worker = FormatsWorker(url, self.formats_signals)
        self.formats_worker.start()

    def on_error_formats(self, msg):
        """Handle format loading error."""
        self.results_list.setEnabled(True)
        self.status_label.setText("⚠️ Error loading formats")
        self.spinner.hide()
        QMessageBox.critical(self, "Format Error", f"Failed to load formats:\n\n{msg}")

    def show_formats_dialog(self, video_url, formats):
        """Show format selection dialog."""
        self.results_list.setEnabled(True)
        self.status_label.setText("")
        self.spinner.hide()

        if not formats:
            QMessageBox.information(self, "No formats", "No playable formats found.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Choose Quality")
        dlg.setModal(True)
        dlg.resize(700, 500)
        dlg.setStyleSheet(self.styleSheet())
        v = QVBoxLayout(dlg)
        v.setSpacing(12)
        v.setContentsMargins(16, 16, 16, 16)
        
        title_label = QLabel("Select Quality:")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        v.addWidget(title_label)
        
        listw = QListWidget()
        listw.setStyleSheet(self.styleSheet())

        seen = set()
        def fmt_key(f):
            h = f.get("height") or 0
            t = f.get("tbr") or 0
            return (h, t)

        for f in sorted(formats, key=fmt_key, reverse=True):
            fmt_id = f.get("format_id")
            if not fmt_id or fmt_id in seen:
                continue
            seen.add(fmt_id)
            
            desc_parts = []
            resolution = f.get("resolution") or f.get("height")
            if resolution:
                desc_parts.append(str(resolution))
            vcodec = f.get("vcodec")
            acodec = f.get("acodec")
            if vcodec and vcodec != "none":
                desc_parts.append(vcodec)
            if acodec and acodec != "none":
                desc_parts.append(acodec)
            filesize = f.get("filesize") or f.get("filesize_approx")
            if filesize:
                try:
                    mb = int(filesize) / (1024 * 1024)
                    desc_parts.append(f"{mb:.1f}MB")
                except:
                    pass
            fps = f.get("fps")
            if fps:
                desc_parts.append(f"{fps}fps")
            tbr = f.get("tbr")
            if tbr:
                desc_parts.append(f"{tbr}kbps")
            
            desc = ", ".join(desc_parts) if desc_parts else f.get("format")
            
            height = f.get("height")
            res = f.get("resolution")
            label = None
            if height:
                label = f"{height}p"
            elif isinstance(res, str) and "x" in res:
                try:
                    label = f"{res.split('x')[-1]}p"
                except:
                    label = None
            if not label:
                tbr = f.get("tbr")
                acodec = f.get("acodec")
                if acodec == "none" and tbr:
                    label = f"{int(tbr)}kbps"
            if not label:
                label = fmt_id

            item = QListWidgetItem(label)
            item.setToolTip(f"{fmt_id} — {desc}")
            item.setData(Qt.UserRole, fmt_id)
            listw.addItem(item)

        v.addWidget(QLabel("Double-click to play:"))
        v.addWidget(listw)

        # Add to favorites button
        fav_layout = QHBoxLayout()
        fav_btn = QPushButton("⭐ Add to Favorites")
        fav_btn.setObjectName("primary")
        fav_btn.clicked.connect(lambda: self.add_to_favorites(video_url))
        fav_layout.addWidget(fav_btn)
        fav_layout.addStretch()
        v.addLayout(fav_layout)

        btns = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.setObjectName("secondary")
        btn_close.clicked.connect(dlg.reject)
        btn_play_best = QPushButton("▶ Play Best Quality")
        btn_play_best.setObjectName("primary")
        btn_play_best.clicked.connect(lambda: self.play_with_mpv(video_url, "best", dlg))
        btns.addStretch()
        btns.addWidget(btn_play_best)
        btns.addWidget(btn_close)
        v.addLayout(btns)

        listw.itemActivated.connect(lambda it: self.play_with_mpv(video_url, it.data(Qt.UserRole), dlg))
        dlg.exec()

    def play_with_mpv(self, video_url, format_id, dialog):
        """Play video with mpv."""
        dialog.accept()
        mpv_path = self.mpv_path_input.text().strip() or "mpv"
        
        if not shutil.which(mpv_path):
            QMessageBox.critical(self, "Error", "mpv not found. Check your mpv path.")
            return

        cmd = [mpv_path, f"--ytdl-format={format_id}", video_url]
        self.setEnabled(False)
        self.status_label.setText("▶ Playing in mpv...")

        playback_signals = WorkerSignals()
        playback_signals.finished.connect(self._on_playback_finished)
        playback_signals.error.connect(self._on_playback_error)

        def run_and_wait():
            try:
                proc = subprocess.Popen(cmd)
                proc.wait()
            except Exception as e:
                playback_signals.error.emit(str(e))
            finally:
                playback_signals.finished.emit()

        t = threading.Thread(target=run_and_wait, daemon=True)
        t.start()

    def _on_playback_finished(self):
        """Called when playback finishes."""
        self.setEnabled(True)
        self.status_label.setText("")

    def _on_playback_error(self, msg):
        """Handle playback error."""
        QMessageBox.critical(self, "Playback Error", f"Error:\n\n{msg}")

    def add_to_favorites(self, video_url):
        """Add current video to favorites."""
        item = self.results_list.currentItem()
        if item:
            widget = self.results_list.itemWidget(item)
            if widget and hasattr(widget, 'entry'):
                entry = widget.entry
                video_data = {
                    "title": entry.get("title", "Unknown"),
                    "url": video_url,
                    "duration": entry.get("duration"),
                }
                self.storage.add_favorite(video_data)
                QMessageBox.information(self, "Added", "Video added to favorites!")
                self.refresh_favorites()

    def refresh_favorites(self):
        """Refresh favorites list."""
        self.favorites_list.clear()
        for fav in self.storage.data.get("favorites", []):
            item = QListWidgetItem(fav.get("title", "Unknown"))
            item.setData(Qt.UserRole, fav.get("url"))
            self.favorites_list.addItem(item)

    def play_favorite(self, item: QListWidgetItem):
        """Play favorite video."""
        url = item.data(Qt.UserRole)
        self.search_input.setText(url)
        self.play_with_mpv(url, "best", QDialog(self))

    def test_mpv(self):
        """Test mpv installation."""
        mpv_path = self.mpv_path_input.text().strip() or "mpv"
        if shutil.which(mpv_path):
            self.storage.data["mpv_path"] = mpv_path
            self.storage.save()
            QMessageBox.information(self, "✓ Success", f"Found mpv at:\n{mpv_path}")
        else:
            QMessageBox.warning(self, "✗ Not Found", "mpv not found in PATH.")

    def open_settings(self):
        """Open settings dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        dlg.setModal(True)
        dlg.resize(400, 300)
        dlg.setStyleSheet(self.styleSheet())
        v = QVBoxLayout(dlg)
        v.setSpacing(12)
        v.setContentsMargins(16, 16, 16, 16)

        title = QLabel("⚙️ Settings")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        v.addWidget(title)

        # Default quality preference
        v.addWidget(QLabel("Default Quality:"))
        quality_combo = QComboBox()
        quality_combo.addItems(["best", "worst", "720p", "480p", "360p", "144p"])
        quality_combo.setCurrentText(self.storage.get_setting("default_quality", "best"))
        v.addWidget(quality_combo)

        # Auto-start with last search
        auto_check = QCheckBox("Auto-start with last search on launch")
        auto_check.setChecked(self.storage.get_setting("auto_start_last", False))
        v.addWidget(auto_check)

        v.addStretch()

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(lambda: self.save_settings(quality_combo, auto_check, dlg))
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondary")
        close_btn.clicked.connect(dlg.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)
        v.addLayout(btn_layout)

        dlg.exec()

    def save_settings(self, quality_combo, auto_check, dialog):
        """Save settings."""
        self.storage.set_setting("default_quality", quality_combo.currentText())
        self.storage.set_setting("auto_start_last", auto_check.isChecked())
        QMessageBox.information(self, "Saved", "Settings saved!")
        dialog.accept()

    def install_ffmpeg(self):
        """Install ffmpeg."""
        if not hasattr(self, 'ffmpeg_install_btn'):
            return
        self.ffmpeg_install_btn.setEnabled(False)

        signals = WorkerSignals()
        signals.results.connect(self._on_ffmpeg_installed)
        signals.error.connect(lambda msg: QMessageBox.critical(self, "Error", msg))
        signals.finished.connect(lambda: self.ffmpeg_install_btn.setEnabled(True))

        def do_install():
            try:
                if os.name != 'nt' and not sys.platform.startswith('win'):
                    signals.error.emit('Auto-install only works on Windows.')
                    return

                url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
                tmp_fd, tmp_path = tempfile.mkstemp(suffix='.zip')
                os.close(tmp_fd)
                urllib.request.urlretrieve(url, tmp_path)
                tmpdir = tempfile.mkdtemp()
                try:
                    with zipfile.ZipFile(tmp_path, 'r') as zf:
                        zf.extractall(tmpdir)
                    ffpath = None
                    for root, dirs, files in os.walk(tmpdir):
                        if 'ffmpeg.exe' in files:
                            ffpath = os.path.join(root, 'ffmpeg.exe')
                            break
                    if not ffpath:
                        signals.error.emit('ffmpeg.exe not found in archive')
                        return
                    dest_dir = os.path.join(os.path.expanduser('~'), '.youtube_mpv', 'bin')
                    os.makedirs(dest_dir, exist_ok=True)
                    dest = os.path.join(dest_dir, 'ffmpeg.exe')
                    shutil.copy2(ffpath, dest)
                    os.environ['PATH'] = dest_dir + os.pathsep + os.environ.get('PATH', '')
                    signals.results.emit(f'Installed to {dest}')
                finally:
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
            except Exception as e:
                signals.error.emit(str(e))
            finally:
                signals.finished.emit()

        t = threading.Thread(target=do_install, daemon=True)
        t.start()

    def _on_ffmpeg_installed(self, msg):
        """Called when ffmpeg installs."""
        try:
            self.ffmpeg_warn.setText(f"✓ {msg}")
            self.ffmpeg_warn.setStyleSheet('color: green; font-weight: 500;')
        except:
            pass

    def play_best_for_selection(self):
        """Play best quality for selected result."""
        item = self.results_list.currentItem()
        if not item:
            QMessageBox.information(self, "No Selection", "Select a result first.")
            return
        url = item.data(Qt.UserRole)
        self.play_with_mpv(url, "best", QDialog(self))





def main():
    app = QApplication([])
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
