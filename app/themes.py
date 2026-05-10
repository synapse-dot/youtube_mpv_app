class Themes:
    DEFAULT = {
        "name": "DEFAULT",
        "bg": "#0a0a0c",
        "sidebar_bg": "#101318",
        "item_bg": "#0f1115",
        "text": "#eaf2ff",
        "text_alt": "#c6d4ef",
        "accent": "#6cb4ff",
        "font": "'JetBrains Mono', 'Consolas', monospace",
        "layout": "sidebar-left",
        "border_width": "1px",
        "border_color": "#293241",
        "radius": "0px",
        "btn_bg": "#1b2638",
        "btn_text": "#eaf2ff",
        "item_padding": 10
    }

    @classmethod
    def get_all(cls):
        return [cls.DEFAULT]

    @classmethod
    def get(cls, name):
        for t in cls.get_all():
            if t["name"] == name: return t
        return cls.DEFAULT
