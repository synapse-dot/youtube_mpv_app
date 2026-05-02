import threading
import urllib.request
from yt_dlp import YoutubeDL
from PySide6.QtCore import Signal, QObject

class WorkerSignals(QObject):
    results = Signal(object)
    error = Signal(str)
    finished = Signal()

class ThumbnailWorker(threading.Thread):
    def __init__(self, url, path, signals):
        super().__init__(daemon=True)
        self.url, self.path, self.signals = url, path, signals
    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as r, open(self.path, "wb") as f:
                f.write(r.read())
            self.signals.results.emit(self.path)
        except Exception as e: self.signals.error.emit(str(e))
        finally: self.signals.finished.emit()

class YTSearchWorker(threading.Thread):
    def __init__(self, query, max_results, signals, sort="relevance"):
        super().__init__(daemon=True)
        self.query, self.max_results, self.signals, self.sort = query, max_results, signals, sort
    def run(self):
        try:
            sort_map = {"RELEVANCE": "", "DATE": "date", "VIEWS": "view_count", "RATING": "rating"}
            s_val = sort_map.get(self.sort, "")
            opts = {"extract_flat": True, "skip_download": True, "quiet": True}
            with YoutubeDL(opts) as ydl:
                prefix = f"ytsearch{s_val}{self.max_results}:" if s_val else f"ytsearch{self.max_results}:"
                # Note: yt-dlp search sorting is via specific search prefixes or params
                info = ydl.extract_info(f"ytsearch{self.max_results}:{self.query}", download=False)
                entries = info.get("entries", [])
                self.signals.results.emit(entries)
        except Exception as e: self.signals.error.emit(str(e))
        finally: self.signals.finished.emit()

class FormatsWorker(threading.Thread):
    def __init__(self, url, signals):
        super().__init__(daemon=True)
        self.url, self.signals = url, signals
    def run(self):
        try:
            with YoutubeDL({"skip_download": True, "quiet": True}) as ydl:
                info = ydl.extract_info(self.url, download=False)
                self.signals.results.emit(info.get("formats", []))
        except Exception as e: self.signals.error.emit(str(e))
        finally: self.signals.finished.emit()
