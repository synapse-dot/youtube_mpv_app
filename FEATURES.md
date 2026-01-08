# mpvTube - Enhanced Features Guide

## 🎨 Gorgeous UI Redesign
- **Modern color scheme**: Sleek blues (#2d8cff), grays, and white with gradients
- **Smooth animations**: Rotating spinner during search/format loading
- **Professional spacing**: Better margins, padding, and layout alignment
- **Responsive design**: Resizable window (1000x800 default, 800x600 minimum)
- **Enhanced focus states**: Clear visual feedback on all interactive elements

## 🔍 Advanced Search Features

### Search History
- **Dropdown list** of recent searches (last 20)
- Quickly re-run previous searches by selecting from dropdown
- Automatically saved to persistent storage

### Cancel Operations
- **Cancel button** appears during search/format fetch
- Press to stop ongoing operations
- Reduces unnecessary network calls if you change your mind

## ⭐ Favorites System
- **Quick-access favorites** panel with 80px height
- **Add to favorites** button in quality selection dialog
- Click to play favorite videos instantly
- Stores up to 50 favorite videos with metadata
- Persistent across app restarts

## 📊 Enhanced Search Results Display

### For Each Result:
- **Video title** (bold, large font)
- **Duration** with formatted time (⏱ MM:SS)
- **Upload date** in readable format (📅 Mon DD, YYYY)
- **Copy URL button** (📋) for easy sharing
- **Custom widget** design with better visual hierarchy

### Sorting & Filtering:
- **Relevance** (default YouTube order)
- **Duration (Short)** - shortest first
- **Duration (Long)** - longest first
- **Newest** - by upload date descending
- **Oldest** - by upload date ascending

Sorting dropdown is always visible above results list.

## ⚙️ Settings Panel
Access via the **⚙️ Settings** button in the top bar.

### Available Settings:
1. **Default Quality Preference**
   - Options: best, worst, 720p, 480p, 360p, 144p
   - Used as default for playback

2. **Auto-start with Last Search**
   - Checkbox option
   - When enabled, app loads the last search on startup
   - Useful for quick access to your most-watched content

### Settings Storage:
- All settings saved in `~/.youtube_mpv_config.json`
- Persists across app restarts

## 💾 Persistent Storage

All data stored in `~/.youtube_mpv_config.json`:

```json
{
  "mpv_path": "path/to/mpv",
  "history": ["query1", "query2", ...],
  "favorites": [
    {"title": "video title", "url": "https://...", "duration": 180},
    ...
  ],
  "settings": {
    "default_quality": "best",
    "auto_start_last": false,
    "max_results": 10
  }
}
```

## 🎯 Workflow Examples

### Example 1: Find and Favorite a Song
1. Type song title in search box
2. Set results to 10-15
3. Press Search
4. Double-click a result to view formats
5. Click "⭐ Add to Favorites" button
6. Select quality and press "▶ Play Best Quality"

### Example 2: Quick Replay from History
1. Click "📋 Recent Searches..." dropdown
2. Select previous search query
3. Results auto-load with previous search
4. Double-click to play

### Example 3: Customize Quality Settings
1. Press "⚙️ Settings"
2. Set "Default Quality" to 480p
3. Check "Auto-start with Last Search"
4. Click Save
5. Next launch will auto-load last search at 480p

## 🚀 Pro Tips

1. **Copy URLs Easily**: Click the "📋 Copy URL" button on any result to copy to clipboard
2. **Skip Format Dialog**: Click "▶ Play Best Quality" in any dialog to play immediately
3. **Organize Searches**: Keep your history clean by regularly searching new content
4. **Batch Favorites**: Add multiple videos to favorites for a personalized quick-access library
5. **Export URLs**: Copy multiple URLs and batch them for external scripts

## 🎬 Keyboard Shortcuts
- **Enter** in search box: Start search
- **Double-click** on result: Open quality selector
- **Double-click** in format list: Play selected format
- **Double-click** on favorite: Play with best quality

## 📝 Version Features
**mpvTube v2.0 with Enhanced Features**:
- ✅ Search history with dropdown
- ✅ Favorites system
- ✅ Animated loading spinner
- ✅ Cancel operations
- ✅ Video metadata (duration, date)
- ✅ Copy URL per result
- ✅ Sort/filter options
- ✅ Settings panel
- ✅ Gorgeous modern UI
- ✅ Persistent storage
