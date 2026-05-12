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

## TUI Features
The new curses-based TUI provides:
- Interactive search within the terminal.
- Browse results with arrow keys.
- Choose video and audio quality separately.
- Manage search history and bookmarks.
- Quick navigation: `/` for search, `h` for history, `b` for bookmarks.

Run with the included Windows helper `run.bat` (recommended): this script prefers a Conda environment named `youtube_mpv` if `conda` is available; otherwise it creates/uses a local virtualenv `.venv`.

From a PowerShell or cmd prompt in the project folder:

```powershell
cmd /c run.bat
```

Notes:
- If `conda` is present, `run.bat` will create and activate an env named `youtube_mpv` and install the requirements there.
- If `conda` is not present, `run.bat` will create a `.venv` virtual environment and install requirements.
- The app saves your `mpv` path to `~/.youtube_mpv_config.json` when you click "Test mpv".
- If `ffmpeg` is missing, the app shows a warning and includes an "Install ffmpeg (auto)" helper that downloads a Windows static build and places `ffmpeg.exe` in `~/.youtube_mpv/bin`.

Notes
- The app uses `yt-dlp` to query YouTube and list formats. mpv is launched externally with `--ytdl-format=<format_id>` and the YouTube URL.
- On Windows, ensure `mpv.exe` is in your PATH or set the MPV path in the small field at the top of the app.
