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
                "default_quality": "best",
                "auto_start_last": False,
                "max_results": 10,
            },
        }

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def add_to_history(self, query):
        if query not in self.data["history"]:
            self.data["history"].insert(0, query)
            self.data["history"] = self.data["history"][:20]
            self.save()

    def get_setting(self, k, d=None):
        return self.data["settings"].get(k, d)
