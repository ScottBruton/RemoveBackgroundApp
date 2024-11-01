# AppMain.py
import threading
import keyboard
from ImageCapture import select_area  # Import select_area to trigger screen selection
from AppControl import setup_tray     # This will handle the tray icon and associated functions

if __name__ == "__main__":
    # Set up tray and hotkeys
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    # Hotkey to start area selection
    keyboard.add_hotkey("ctrl+alt+s", lambda: select_area())
    keyboard.add_hotkey("ctrl+alt+q", lambda: exit(0))

    print("Running in system tray. Press Ctrl+Alt+S to capture screen selection. Press Ctrl+Alt+Q to exit.")
    keyboard.wait("esc")
