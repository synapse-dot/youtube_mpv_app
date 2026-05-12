import locale
import subprocess
from typing import Dict, Any

from yt_dlp import YoutubeDL
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, ListItem, ListView, Static, Label
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.binding import Binding

from app.storage import StorageManager

def _lang_code():
    loc = locale.getlocale()[0] or "en_US"
    return loc.split("_")[0].lower()

class ResultItem(ListItem):
    def __init__(self, entry: Dict[str, Any]):
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        title = self.entry.get("title", "Untitled")
        uploader = self.entry.get("uploader", "Unknown channel")
        duration = self.entry.get("duration_string", "??:??")
        yield Label(f"[b]{title}[/b]")
        yield Label(f"[dim]{uploader} • {duration}[/dim]")

class FormatItem(ListItem):
    def __init__(self, label: str, format_id: str):
        super().__init__()
        self.label = label
        self.format_id = format_id

    def compose(self) -> ComposeResult:
        yield Label(self.label)


class HistoryItem(ListItem):
    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def compose(self) -> ComposeResult:
        yield Label(self.query)

class FormatSelectionModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Play"),
        Binding("tab", "focus_next", "Next"),
    ]

    def __init__(self, url: str, title: str):
        super().__init__()
        self.url = url
        self.video_title = title
        self.formats = []
        self.videos = []
        self.audios = []

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"Select Quality for: [b]{self.video_title}[/b]", id="modal-title"),
            Vertical(
                Label("Video Quality"),
                ListView(id="video-list"),
                Label("Audio Quality"),
                ListView(id="audio-list"),
                id="modal-content"
            ),
            Horizontal(
                Static("Press [b]Enter[/b] to play • [b]Esc[/b] to cancel", id="modal-hint"),
            ),
            id="modal-dialog"
        )

    async def on_mount(self) -> None:
        self.run_worker(self.fetch_formats(), thread=True)

    async def fetch_formats(self):
        try:
            with YoutubeDL({"skip_download": True, "quiet": True}) as ydl:
                info = ydl.extract_info(self.url, download=False)
                self.formats = info.get("formats", [])
            
            seen_v, seen_a = set(), set()
            for f in sorted([x for x in self.formats if x.get("height") and x.get("vcodec") != "none"], key=lambda x: x.get("height", 0), reverse=True):
                label = f"{f.get('height')}p • {f.get('ext')}"
                if label not in seen_v:
                    seen_v.add(label)
                    self.videos.append((label, f.get("format_id")))
            
            for f in sorted([x for x in self.formats if x.get("abr") and x.get("vcodec") == "none"], key=lambda x: x.get("abr", 0), reverse=True):
                label = f"{int(f.get('abr', 0))} kbps"
                if label not in seen_a:
                    seen_a.add(label)
                    self.audios.append((label, f.get("format_id")))

            self.call_from_thread(self.update_lists)
        except Exception as e:
            self.app.notify(f"Error fetching formats: {e}", severity="error")
            self.dismiss(None)

    def update_lists(self):
        v_list = self.query_one("#video-list", ListView)
        a_list = self.query_one("#audio-list", ListView)
        for label, fid in self.videos:
            v_list.append(FormatItem(label, fid))
        for label, fid in self.audios:
            a_list.append(FormatItem(label, fid))
        if self.videos:
            v_list.index = 0
            v_list.focus()
        if self.audios:
            a_list.index = 0

    def action_cancel(self):
        self.dismiss(None)

    def action_confirm(self):
        v_list = self.query_one("#video-list", ListView)
        a_list = self.query_one("#audio-list", ListView)
        
        vid = v_list.highlighted_child.format_id if v_list.highlighted_child else None
        aid = a_list.highlighted_child.format_id if a_list.highlighted_child else None
        
        fmt = f"{vid}+{aid}" if (vid and aid) else (vid or aid)
        if not fmt:
            self.app.notify("Pick at least one format", severity="warning")
            return
        self.dismiss(fmt)

class MpvTubeApp(App):
    CSS = """
    Screen {
        background: $surface;
    }
    #search-container {
        padding: 1 2;
        height: auto;
    }
    #results-list {
        border: round $accent;
        margin: 1 2;
    }
    ResultItem {
        padding: 1 1;
        height: auto;
    }
    ResultItem Label {
        width: 100%;
    }
    #modal-dialog {
        background: $surface;
        border: thick $accent;
        padding: 1 2;
        width: 60;
        height: 34;
        align: center middle;
    }
    #modal-title {
        text-align: center;
        padding-bottom: 1;
    }
    #modal-content {
        height: 1fr;
    }
    #modal-hint {
        padding-top: 1;
        text-align: center;
        width: 100%;
    }
    ListView {
        background: $surface;
        border: solid $primary;
        height: 1fr;
        min-height: 8;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("/", "focus_search", "Search", show=True),
        Binding("h", "show_history", "History", show=True),
        Binding("b", "show_bookmarks", "Bookmarks", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.storage = StorageManager()
        self.lang = _lang_code()
        self.results = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Input(placeholder="Search YouTube...", id="search-input"),
            id="search-container"
        )
        yield ListView(id="results-list")
        yield Footer()

    def action_focus_search(self):
        self.query_one("#search-input").focus()

    async def on_input_submitted(self, event: Input.Submitted):
        query = event.value.strip()
        if query:
            self.storage.add_to_history(query)
            await self.perform_search(query)

    async def perform_search(self, query: str):
        self.query_one("#results-list").clear()
        self.notify(f"Searching for: {query}")
        self.run_worker(self.fetch_results(query), thread=True)

    async def fetch_results(self, query: str):
        try:
            with YoutubeDL({"extract_flat": True, "skip_download": True, "quiet": True}) as ydl:
                info = ydl.extract_info(f"ytsearch15:{query}", download=False)
            entries = info.get("entries", [])[:15]
            self.call_from_thread(self.update_results, entries)
        except Exception as e:
            self.app.notify(f"Search failed: {e}", severity="error")

    def update_results(self, entries):
        results_list = self.query_one("#results-list", ListView)
        results_list.clear()
        self.results = entries
        for entry in entries:
            results_list.append(ResultItem(entry))
        if entries:
            results_list.focus()

    def _on_format_selected(self, url: str, fmt: str | None):
        if fmt:
            self.launch_mpv(url, fmt)

    def on_list_view_selected(self, event: ListView.Selected):
        item = event.item
        if isinstance(item, ResultItem):
            entry = item.entry
            url = entry.get("webpage_url") or entry.get("url")
            if url and not url.startswith("http"):
                url = f"https://youtube.com/watch?v={url}"
            
            if url:
                self.push_screen(
                    FormatSelectionModal(url, entry.get("title", "Unknown")),
                    callback=lambda fmt: self._on_format_selected(url, fmt),
                )
        elif isinstance(item, HistoryItem):
            self.query_one("#search-input", Input).value = item.query
            self.query_one("#search-input", Input).focus()

    def action_show_history(self):
        results_list = self.query_one("#results-list", ListView)
        results_list.clear()
        for h in self.storage.data["history"]:
            results_list.append(HistoryItem(h))
        results_list.focus()

    def action_show_bookmarks(self):
        results_list = self.query_one("#results-list", ListView)
        results_list.clear()
        for f in self.storage.data["favorites"]:
            item = ResultItem({"title": f["title"], "url": f["url"], "uploader": "Bookmark"})
            results_list.append(item)
        results_list.focus()

    def launch_mpv(self, url: str, fmt: str):
        self.notify("Preparing playback...", title="MpvTube", severity="information")
        
        # Use storage path if set, otherwise fallback to system mpv
        mpv_path = self.storage.data.get("mpv_path", "mpv")
        
        cmd = [
            mpv_path, "--no-terminal", "--msg-level=all=no",
            "--prefetch-playlist=yes", "--cache=yes",
            f"--alang={self.lang}", f"--slang={self.lang}", f"--ytdl-format={fmt}", url,
        ]
        
        try:
            import shutil
            # Verify executable exists
            actual_path = shutil.which(mpv_path)
            if not actual_path and mpv_path and "/" in mpv_path:
                actual_path = mpv_path if subprocess.os.path.exists(mpv_path) else None
            if not actual_path:
                raise FileNotFoundError(f"Could not find mpv at '{mpv_path}'")

            # Launch in background without closing TUI
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.notify("Playback started in mpv", title="Success", severity="information")
            
        except FileNotFoundError as e:
            self.notify(f"[b]Error:[/b] {str(e)}\nPlease install mpv or update path in settings.", 
                        title="Launch Failed", severity="error", timeout=10)
        except Exception as e:
            self.notify(f"Unexpected error: {str(e)}", title="Launch Failed", severity="error", timeout=10)

def run_tui():
    app = MpvTubeApp()
    app.run()

def run_tui_min():
    # Keep the minimal version as a simple line-based fallback
    from app.storage import StorageManager
    from yt_dlp import YoutubeDL
    import subprocess
    import locale

    def _lang_code():
        loc = locale.getlocale()[0] or "en_US"
        return loc.split("_")[0].lower()

    def _pick(prompt, options):
        print(f"\n{prompt}")
        for i, label in enumerate(options, 1):
            print(f"  {i}. {label}")
        while True:
            raw = input("Select number (or q): ").strip().lower()
            if raw == "q": return None
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                return int(raw) - 1
            print("Invalid selection, try again.")

    storage = StorageManager()
    lang = _lang_code()
    print("MpvTube TUI (Minimal)")
    query = input("Search YouTube: ").strip()
    if not query or query.lower() == "q": return

    with YoutubeDL({"extract_flat": True, "skip_download": True, "quiet": True}) as ydl:
        info = ydl.extract_info(f"ytsearch15:{query}", download=False)
    entries = info.get("entries", [])
    if not entries:
        print("No results found.")
        return

    labels = [f"{e.get('title', 'Untitled')} — {e.get('uploader', 'Unknown channel')}" for e in entries[:15]]
    pick_idx = _pick("Search results", labels)
    if pick_idx is None: return
    entry = entries[pick_idx]
    url = entry.get("webpage_url") or entry.get("url")
    if url and not url.startswith("http"):
        url = f"https://youtube.com/watch?v={url}"
    
    with YoutubeDL({"skip_download": True, "quiet": True}) as ydl:
        formats = ydl.extract_info(url, download=False).get("formats", [])

    videos, audios = [], []
    seen = set()
    for f in sorted([x for x in formats if x.get("height") and x.get("vcodec") != "none"], key=lambda x: x.get("height", 0), reverse=True):
        label = f"{f.get('height')}p • {f.get('ext')}"
        if label in seen: continue
        seen.add(label)
        videos.append((label, f.get("format_id")))

    seen = set()
    for f in sorted([x for x in formats if x.get("abr") and x.get("vcodec") == "none"], key=lambda x: x.get("abr", 0), reverse=True):
        label = f"{int(f.get('abr', 0))} kbps"
        if label in seen: continue
        seen.add(label)
        audios.append((label, f.get("format_id")))

    vid_idx = _pick("Video quality", [v[0] for v in videos]) if videos else None
    aid_idx = _pick("Audio quality", [a[0] for a in audios]) if audios else None

    vid = videos[vid_idx][1] if vid_idx is not None else None
    aid = audios[aid_idx][1] if aid_idx is not None else None
    fmt = f"{vid}+{aid}" if (vid and aid) else (vid or aid)
    
    cmd = [
        storage.data["mpv_path"], "--no-terminal", "--msg-level=all=no",
        "--prefetch-playlist=yes", "--cache=yes",
        f"--alang={lang}", f"--slang={lang}", f"--ytdl-format={fmt}", url,
    ]
    subprocess.Popen(cmd)
    print("Playback launched.")
