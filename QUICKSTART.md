# 🎬 mpvTube Enhanced - Quick Start Guide

## Installation & Setup

### Prerequisites
```bash
pip install PySide6 yt-dlp
```

On Windows (recommended):
```bash
# Install ffmpeg (optional but recommended)
# Or use the app's built-in "Install ffmpeg" button
```

### Run the App
```bash
python main.py
```

## ⚡ Quick Features Tour

### 1. First Search
- Type a video title or URL in search box
- Adjust results count (default: 10)
- Press Search or Enter key
- Watch the animated spinner ✨

### 2. View Results
- **Duration**: ⏱ MM:SS format
- **Upload Date**: 📅 Month DD, YYYY
- **Copy URL**: Click 📋 button to copy
- **Double-click**: Open quality selector

### 3. Search History
- Click "📋 Recent Searches..." dropdown
- Select any previous search to re-run
- Automatically populated with last 20 searches

### 4. Add to Favorites
- Double-click any result
- Click "⭐ Add to Favorites" in dialog
- Access from Favorites panel below search bar
- Double-click favorite to play instantly

### 5. Sort Results
- Use "Sort" dropdown above results
- Options:
  - Relevance (default)
  - Duration (Short)
  - Duration (Long)
  - Newest
  - Oldest

### 6. Customize Settings
- Click "⚙️ Settings" button
- Set default quality preference
- Enable auto-start with last search
- Click Save

### 7. Play Videos
- **Format Selection**: Double-click result → choose quality → double-click format
- **Play Best Quality**: Click "▶ Play Best Quality" button to skip format dialog
- **Quick Play**: Click "▶ Play Best" button in top bar

## 🎮 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Search in search box |
| Double-click | Open quality selector on result |
| Double-click | Play selected format |
| Double-click | Play favorite |

## 🛠️ Troubleshooting

### mpv not found
- Click "🧪 Test" to verify mpv installation
- Check mpv path in top bar (default: "mpv")
- If not in PATH, provide full path (e.g., C:\Program Files\mpv\mpv.exe)

### ffmpeg warning
- Click "Install ffmpeg" button in warning banner
- Or install manually: https://ffmpeg.org/download.html

### Search fails
- Check internet connection
- Try simpler search term
- Check if YouTube is accessible in your region

### Settings not saving
- Ensure ~/.youtube_mpv_config.json is writable
- Check home directory permissions

## 📁 Data Files

Config file location: `~/.youtube_mpv_config.json`

Contains:
- Search history (last 20)
- Favorites (last 50)
- Settings (quality, auto-start)
- mpv path

You can manually edit or delete this file if needed.

## 🎨 UI Customization

To change colors, edit the `apply_stylesheet()` method in MainWindow class:

```python
def apply_stylesheet(self):
    stylesheet = """
        # Modify these colors:
        background-color: #f8f9fa;  # Light gray background
        #2d8cff;                     # Primary blue
        #e8e8e8;                     # Secondary gray
        ...
    """
```

## 🚀 Advanced Tips

### Batch Operations
- Copy multiple URLs from results
- Paste into external scripts
- Create playlists

### Integration
- Use with other tools
- Export favorites as text
- Share favorites via config file

### Performance
- Search for shorter terms to get faster results
- Lower result count for quicker searches
- Skip format dialog by clicking "Play Best"

## 💡 Best Practices

1. **Search Smart**: Use video title + artist for music
2. **Organize Favorites**: Keep frequently-used videos in favorites
3. **Sort Strategically**: Sort by duration to find the right length
4. **Save Settings**: Set your preferred quality to avoid repeating
5. **Update History**: Regularly search new content to keep history fresh

## 📞 Support

For issues with:
- **yt-dlp**: Visit https://github.com/yt-dlp/yt-dlp
- **mpv**: Visit https://mpv.io
- **PySide6**: Visit https://doc.qt.io/qtforpython

## 🎉 Enjoy!

You now have a beautiful, feature-rich YouTube player with:
- ✨ Modern, gorgeous UI
- 🔍 Powerful search with history
- ⭐ Favorites system
- 📊 Advanced sorting
- ⚙️ Customizable settings
- 🎬 High-quality video playback

Happy watching! 🍿
