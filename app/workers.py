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
        self.url = url
        self.path = path
        self.signals = signals

    def run(self):
        try:
            req = urllib.request.Request(
                self.url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            with urllib.request.urlopen(req) as response:
                with open(self.path, "wb") as f:
                    f.write(response.read())
            self.signals.results.emit(self.path)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class YTSearchWorker(threading.Thread):
    def __init__(self, query, max_results, signals):
        super().__init__(daemon=True)
        self.query = query
        self.max_results = max_results
        self.signals = signals

    def run(self):
        try:
            with YoutubeDL({"extract_flat": True, "skip_download": True}) as ydl:
                info = ydl.extract_info(f"ytsearch{self.max_results}:{self.query}", download=False)
                self.signals.results.emit(info.get("entries", []))
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


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
