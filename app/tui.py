import locale
import subprocess

from yt_dlp import YoutubeDL

from app.storage import StorageManager


def _lang_code():
    loc = locale.getdefaultlocale()[0] or "en_US"
    return loc.split("_")[0].lower()


def _pick(prompt, options):
    print(f"\n{prompt}")
    for i, label in enumerate(options, 1):
        print(f"  {i}. {label}")
    while True:
        raw = input("Select number (or q): ").strip().lower()
        if raw == "q":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print("Invalid selection, try again.")


def run_tui():
    storage = StorageManager()
    lang = _lang_code()
    print("MpvTube TUI")
    print("Accessible keyboard-first flow. Press q anytime to quit.\n")
    query = input("Search YouTube: ").strip()
    if not query or query.lower() == "q":
        return

    with YoutubeDL({"extract_flat": True, "skip_download": True, "quiet": True}) as ydl:
        info = ydl.extract_info(f"ytsearch15:{query}", download=False)
    entries = info.get("entries", [])
    if not entries:
        print("No results found.")
        return

    labels = [f"{e.get('title', 'Untitled')} — {e.get('uploader', 'Unknown channel')}" for e in entries[:15]]
    pick_idx = _pick("Search results", labels)
    if pick_idx is None:
        return
    entry = entries[pick_idx]
    url = entry.get("webpage_url") or entry.get("url")
    if url and not url.startswith("http"):
        url = f"https://youtube.com/watch?v={url}"
    if not url:
        print("Could not resolve video URL.")
        return

    with YoutubeDL({"skip_download": True, "quiet": True}) as ydl:
        formats = ydl.extract_info(url, download=False).get("formats", [])

    videos = []
    seen = set()
    for f in sorted([x for x in formats if x.get("height") and x.get("vcodec") != "none"], key=lambda x: x.get("height", 0), reverse=True):
        label = f"{f.get('height')}p • {f.get('ext')}"
        if label in seen:
            continue
        seen.add(label)
        videos.append((label, f.get("format_id")))

    audios = []
    seen = set()
    for f in sorted([x for x in formats if x.get("abr") and x.get("vcodec") == "none"], key=lambda x: x.get("abr", 0), reverse=True):
        label = f"{int(f.get('abr', 0))} kbps"
        if label in seen:
            continue
        seen.add(label)
        audios.append((label, f.get("format_id")))

    if not videos and not audios:
        print("No playable formats found.")
        return

    vid_idx = _pick("Video quality", [v[0] for v in videos]) if videos else None
    if videos and vid_idx is None:
        return
    aid_idx = _pick("Audio quality", [a[0] for a in audios]) if audios else None
    if audios and aid_idx is None:
        return

    vid = videos[vid_idx][1] if videos else None
    aid = audios[aid_idx][1] if audios else None
    fmt = f"{vid}+{aid}" if (vid and aid) else (vid or aid)
    if not fmt:
        print("No format selected.")
        return

    cmd = [
        storage.data["mpv_path"],
        "--no-terminal",
        "--msg-level=all=no",
        "--prefetch-playlist=yes",
        "--cache=yes",
        f"--alang={lang}",
        f"--slang={lang}",
        f"--ytdl-format={fmt}",
        url,
    ]
    subprocess.Popen(cmd)
    print("Playback launched. Exiting TUI.")
