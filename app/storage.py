import json
import os

class StorageManager:
    def __init__(self):
        self.config_path = os.path.join(os.path.expanduser("~"), ".youtube_mpv_config.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "mpv_path": "mpv",
            "history": [],
            "favorites": [],
            "settings": {
                "theme": "CYBERPUNK",
                "max_results": 15
            },
        }

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def set_theme(self, theme_name):
        self.data["settings"]["theme"] = theme_name
        self.save()

    def add_to_history(self, query):
        if query in self.data["history"]:
            self.data["history"].remove(query)
        self.data["history"].insert(0, query)
        self.data["history"] = self.data["history"][:25]
        self.save()

    def add_favorite(self, title, url, thumb):
        if any(f["url"] == url for f in self.data["favorites"]):
            return
        self.data["favorites"].insert(0, {"title": title, "url": url, "thumb": thumb})
        self.data["favorites"] = self.data["favorites"][:50]
        self.save()

    def remove_favorite(self, url):
        self.data["favorites"] = [f for f in self.data["favorites"] if f["url"] != url]
        self.save()

    def get_setting(self, k, d=None):
        return self.data["settings"].get(k, d)
