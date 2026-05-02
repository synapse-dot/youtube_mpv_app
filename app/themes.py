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
        "spacing": 0,
        "border": "1px solid #1a1d23",
        "item_border": "1px solid #1a1d23",
        "radius": "0px",
        "padding": "20px",
        "button_style": "sharp-glow"
    }

    BRUTALIST = {
        "name": "BRUTALIST",
        "bg": "#ffffff",
        "sidebar_bg": "#ffffff",
        "item_bg": "#ffffff",
        "text": "#000000",
        "text_alt": "#000000",
        "accent": "#ff3e00",
        "font": "'Archivo Black', 'Arial Black', sans-serif",
        "layout": "top-bar",
        "spacing": 20,
        "border": "4px solid #000000",
        "item_border": "4px solid #000000",
        "radius": "0px",
        "padding": "40px",
        "button_style": "heavy-block"
    }

    VOGUE = {
        "name": "VOGUE",
        "bg": "#f9f7f2",
        "sidebar_bg": "#f9f7f2",
        "item_bg": "transparent",
        "text": "#121212",
        "text_alt": "#444444",
        "accent": "#c5a059",
        "font": "'Playfair Display', 'Georgia', serif",
        "layout": "centered-minimal",
        "spacing": 10,
        "border": "none",
        "item_border": "0 0 1px 0 solid #dcdcdc",
        "radius": "0px",
        "padding": "60px",
        "button_style": "hairline-elegant"
    }

    @classmethod
    def get_all(cls):
        return [cls.CYBERPUNK, cls.BRUTALIST, cls.VOGUE]

    @classmethod
    def get(cls, name):
        for t in cls.get_all():
            if t["name"] == name: return t
        return cls.CYBERPUNK
