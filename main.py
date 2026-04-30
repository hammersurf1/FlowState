import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageFont
import sys

from engine import TypingEngine
from os_layer import get_driver

SHORT_NAMES = {
    "UserMeanDelay": "SPD",
    "UserVariance": "VAR",
    "TypoChance": "ERR",
    "TypoDelay": "FIX",
    "RevisionChance": "REV"
}

def create_image(color, top_text="", bottom_text=""):
    """Generates a dynamic 64x64 colored square with text drawn directly on it"""
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    draw.rectangle((2, 2, 62, 62), fill=color, outline="white", width=2)
    
    if top_text or bottom_text:
        try:
            font_top = ImageFont.load_default(size=18)
            font_bot = ImageFont.load_default(size=26)
        except TypeError:
            font_top = ImageFont.load_default()
            font_bot = ImageFont.load_default()

        if top_text:
            draw.text((32, 20), top_text, fill="white", font=font_top, anchor="mm")
        if bottom_text:
            if top_text in ["ERR", "REV"]:
                bottom_text = f"{bottom_text}%"
            draw.text((32, 46), str(bottom_text), fill="white", font=font_bot, anchor="mm")

    return image

def main():
    try:
        driver = get_driver()
        engine = TypingEngine(driver)
        driver.register_hotkeys(engine)
        
        tray_icon = pystray.Icon("AutoTyper", create_image("blue"), "AutoTyper: Idle")

        def update_tray(*args):
            var_name = engine.settings_list[engine.current_setting_index]
            val = engine.settings[var_name]
            friendly = engine.setting_names[engine.current_setting_index]
            short_name = SHORT_NAMES.get(var_name, "SET")
            
            # --- 1. UPDATE VISUAL ICON ---
            color = "blue"
            
            # If counting down, show RDY + Number
            if engine.is_running and engine.countdown > 0:
                color = "green"
                short_name = "RDY"
                val = engine.countdown
            elif engine.is_running and not engine.is_paused:
                color = "green"
            elif engine.is_paused:
                color = "orange"
                
            tray_icon.icon = create_image(color, top_text=short_name, bottom_text=val)

            # --- 2. UPDATE HOVER TEXT ---
            tray_icon.title = f"AutoTyper\n{friendly}: {val}"

            # --- 3. UPDATE RIGHT-CLICK MENU ---
            menu_items =[]
            status_text = "Status: Running" if engine.is_running and not engine.is_paused else \
                          "Status: Paused" if engine.is_paused else "Status: Idle"
            menu_items.append(item(status_text, lambda: None, enabled=False))
            menu_items.append(item("---", lambda: None, enabled=False))

            for i, v_name in enumerate(engine.settings_list):
                f_name = engine.setting_names[i]
                c_val = engine.settings[v_name]
                prefix = "▶ " if i == engine.current_setting_index else "  "
                menu_items.append(item(f"{prefix}{f_name}: {c_val}", lambda: None, enabled=False))

            menu_items.append(item("---", lambda: None, enabled=False))
            menu_items.append(item("Exit AutoTyper", lambda: tray_icon.stop()))
            
            tray_icon.menu = pystray.Menu(*menu_items)

        def status_changed():
            update_tray()

        engine.ui_update_callback = update_tray
        engine.status_callback = status_changed

        update_tray()

        print("AutoTyper running silently in the system tray.")
        tray_icon.run() 
        
        driver.stop_blocker()
        sys.exit(0)

    except Exception as e:
        print(f"Failed to start: {e}")

if __name__ == "__main__":
    main()