class Themes:
    CYBERPUNK = {
        "name": "CYBERPUNK",
        "bg": "#0a0a0c",
        "sidebar_bg": "#050505",
        "item_bg": "#0f1115",
        "text": "#00ff99",
        "text_alt": "#ffffff",
        "accent": "#ff0055",
        "font": "'JetBrains Mono', 'Consolas', monospace",
        "layout": "sidebar-left",
        "border_width": "1px",
        "border_color": "#1a1d23",
        "radius": "0px",
        "btn_bg": "#111318",
        "btn_text": "#00ff99",
        "item_padding": "10px"
    }

    BRUTALIST = {
        "name": "BRUTALIST",
        "bg": "#ffffff",
        "sidebar_bg": "#000000",
        "item_bg": "#ffffff",
        "text": "#000000",
        "text_alt": "#000000",
        "accent": "#ff3e00",
        "font": "'Archivo Black', 'Arial Black', sans-serif",
        "layout": "top-bar",
        "border_width": "6px",
        "border_color": "#000000",
        "radius": "0px",
        "btn_bg": "#ff3e00",
        "btn_text": "#ffffff",
        "item_padding": "30px"
    }

    VOGUE = {
        "name": "VOGUE",
        "bg": "#f9f7f2",
        "sidebar_bg": "#f9f7f2",
        "item_bg": "transparent",
        "text": "#121212",
        "text_alt": "#888888",
        "accent": "#c5a059",
        "font": "'Playfair Display', 'Georgia', serif",
        "layout": "centered-minimal",
        "border_width": "0px",
        "border_color": "transparent",
        "radius": "0px",
        "btn_bg": "#121212",
        "btn_text": "#f9f7f2",
        "item_padding": "40px"
    }

    @classmethod
    def get_all(cls):
        return [cls.CYBERPUNK, cls.BRUTALIST, cls.VOGUE]

    @classmethod
    def get(cls, name):
        for t in cls.get_all():
            if t["name"] == name: return t
        return cls.CYBERPUNK
