# mpvTube

Simple Python GUI to search YouTube, pick a video, select an available quality, and open mpv to play that exact quality. When mpv closes, the app returns to the main window.

Requirements
- Python 3.10+
- mpv (installed and on PATH, or set path in the app)
- Dependencies in `requirements.txt`

Install (Linux)

```bash
chmod +x install.sh
./install.sh
```

Run

```bash
python main.py        # Default TUI
python main.py --gui  # GUI mode
python main.py --min  # Minimal TUI mode
```

Uninstall (Linux)

```bash
chmod +x uninstall.sh
./uninstall.sh
```


## TUI Features
The Textual-based TUI provides:
- Interactive search within the terminal.
- Browse results with arrow keys.
- Choose video and audio quality separately.
- Manage search history and bookmarks.
- Quick navigation: `/` for search, `h` for history, `b` for bookmarks.

Windows:
- Use the included helper:

```powershell
cmd /c run.bat
```

- If `conda` is available, `run.bat` creates/uses env `youtube_mpv`.
- Otherwise it creates/uses local `.venv`.

Notes:
- The app stores configuration at `~/.config/mpvTube/config.json`.
- GUI includes a **Test mpv** button that validates and saves your mpv path.
- GUI includes **Install ffmpeg (auto)** on Windows, installing `ffmpeg.exe` to `~/.youtube_mpv/bin`.

Notes
- The app uses `yt-dlp` to query YouTube and list formats. mpv is launched externally with `--ytdl-format=<format_id>` and the YouTube URL.
- On Windows, ensure `mpv.exe` is in your PATH or set the MPV path in the small field at the top of the app.
