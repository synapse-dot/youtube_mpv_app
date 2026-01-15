# Implementation Plan for mpvTube - Terminal Edition

## Overview
Enhance main.py with terminal-style aesthetic, working thumbnails, and retro terminal hacks while keeping the classic green-on-black terminal look.

## User Requirements (Clarified)
- Keep **terminal-style aesthetic** (dark background, monospace fonts)
- Add **terminal spinner animation** (retro terminal feel)
- Implement **working YouTube thumbnails** (actual images, not emoji)
- Add favorites, history, settings features with terminal styling
- Retro terminal hacks and visual effects

## Information Gathered

### Current State (main.py):
- Terminal-style green/black theme (already has this)
- Basic search functionality
- Simple results list (text only)
- No thumbnails
- No favorites system
- No history dropdown
- Basic functionality only

### Target State:
- **Terminal-style dark theme** (black #0c0c0c, green #00ff00, amber #ffb000 for accents)
- **Monospace fonts** (Courier New, Consolas, or system terminal font)
- **Animated terminal spinner** (classic terminal spinner characters)
- **Working YouTube thumbnails** (QLabel with QPixmap from thumbnail URLs)
- **Search history dropdown** (last 20 searches)
- **Favorites panel** (quick-access to favorite videos)
- **Settings panel** (quality preference, auto-start)
- **Cancel button** with terminal styling
- **Sort/filter options** for results
- **Retro terminal effects** (scanlines, cursor blink, etc.)

## Plan

### Phase 1: Terminal UI Foundation
1. Define terminal color palette (black bg, green text, amber accents)
2. Set monospace font family (Courier New, Consolas, or system default)
3. Create terminal-style button styles (borders, hover effects)
4. Design layout structure matching terminal emulator look

### Phase 2: Terminal Spinner Animation
5. Implement LoadingSpinner with terminal spinner characters
6. Use classic spinner: `| / - \` or `◐ ◑ ◓ ◒`
7. Add spinner to search and format loading states
8. Style spinner with green color

### Phase 3: Working Thumbnails
9. Add ThumbnailLoader class (threaded image loading)
10. Create ThumbnailWidget for displaying YouTube thumbnails
11. Download/show thumbnails from YouTube API (thumburl field)
12. Handle failed loads with placeholder/style

### Phase 4: Enhanced Results Display
13. Create SearchResultItem with thumbnail + title + metadata
14. Display duration, upload date, view count
15. Add copy URL button per result
16. Style with terminal colors and fonts

### Phase 5: Search History Dropdown
17. Add QComboBox for recent searches
18. Populate from StorageManager history
19. Handle selection to re-run searches
20. Save new searches to history

### Phase 6: Favorites System
21. Add favorites panel (left or bottom section)
22. Add to favorites button in quality dialog
23. Click favorite to play with mpv
24. Persistent storage (up to 50 favorites)

### Phase 7: Settings Panel
25. Create SettingsDialog (modal)
26. Default quality preference (best, 720p, 480p, etc.)
27. Auto-start with last search checkbox
28. Save/load settings in StorageManager

### Phase 8: Sort/Filter Options
29. Add sort dropdown above results
30. Implement sorting: Relevance, Duration (Short/Long), Newest, Oldest
31. Real-time sorting without network calls

### Phase 9: Terminal Polish
32. Add scanline effect overlay (optional)
33. Style status bar with terminal look
34. Add keyboard shortcuts documentation
35. Retro cursor blink effect (optional)

## Files to Modify
- **main.py** - Complete enhancement with all new features

## New Classes to Add
- `LoadingSpinner` - Terminal-style animated spinner
- `ThumbnailLoader` - Threaded thumbnail image loading
- `ThumbnailWidget` - Widget for displaying thumbnails
- `SearchResultItem` - Enhanced result widget with thumbnail
- `SettingsDialog` - Settings modal dialog

## Dependent Files
- No external dependencies (uses PySide6, yt-dlp already available)
- Thumbnails loaded from YouTube's thumbnail URLs

## Followup Steps
1. Test syntax: `python -m py_compile main.py`
2. Test imports: ensure PySide6 and network access for thumbnails
3. Run application: `python main.py`
4. Verify features:
   - Terminal spinner animation works
   - Thumbnails load correctly from YouTube
   - Search history dropdown functions
   - Favorites add/play works
   - Settings persist
   - Sort/filter works
   - Overall terminal aesthetic maintained

## Risk Assessment
- **Low risk**: Enhancement of existing codebase
- **Thumbnail loading**: Requires network, need error handling
- **UI changes**: May need tweaking for best terminal look

## Success Criteria
- Terminal-style aesthetic preserved
- Working YouTube thumbnails displayed
- Animated terminal spinner
- All enhanced features functional (history, favorites, settings)
- No syntax errors
- Application runs without crashes

