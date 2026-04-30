import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import sys

from engine import TypingEngine
from os_layer import get_driver

def create_image(color):
    """Generates a clean 64x64 colored circle to represent state"""
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a nice anti-aliased circle
    draw.ellipse((8, 8, 56, 56), fill=color, outline="white", width=3)
    
    return image

def main():
    try:
        driver = get_driver()
        engine = TypingEngine(driver)
        driver.register_hotkeys(engine)
        
        tray_icon = pystray.Icon("AutoTyper", create_image("#0078D7"), "AutoTyper: Idle")

        def update_tray(*args):
            var_name = engine.settings_list[engine.current_setting_index]
            val = engine.settings[var_name]
            friendly = engine.setting_names[engine.current_setting_index]
            
            # --- 1. UPDATE VISUAL ICON ---
            color = "#0078D7" # Blue
            status_text = "Idle"
            
            if engine.is_running and engine.countdown > 0:
                color = "#FFB900" # Yellow
                status_text = f"Starting in {engine.countdown}..."
            elif engine.is_running and not engine.is_paused:
                color = "#107C10" # Green
                status_text = "Running"
            elif engine.is_paused:
                color = "#D83B01" # Orange
                status_text = "Paused"
                
            tray_icon.icon = create_image(color)

            # --- 2. UPDATE HOVER TEXT ---
            tray_icon.title = f"AutoTyper ({status_text})\n{friendly}: {val}"

            # --- 3. UPDATE RIGHT-CLICK MENU ---
            menu_items =[]
            menu_items.append(item(f"Status: {status_text}", lambda: None, enabled=False))
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