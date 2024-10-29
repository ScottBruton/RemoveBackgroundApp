import threading
import tkinter as tk
from PIL import Image, ImageTk, ImageGrab
import keyboard
import pystray
from pystray import MenuItem as item
from PIL import Image as PilImage  # For icon loading
import sys
import time
import ctypes

# Set DPI awareness to handle high DPI scaling
ctypes.windll.shcore.SetProcessDpiAwareness(2)

# Capture selected area and show image in GUI
def capture_selected_area(x1, y1, x2, y2):
    # Ensure the coordinates are in the correct order
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    
    # Add a small delay to ensure the screen is properly updated before capture
    time.sleep(0.2)
    
    # Grab the selected screen area
    image = ImageGrab.grab(bbox=(x1, y1, x2, y2)).convert("RGBA")
    
    # Initialize the GUI
    root = tk.Tk()
    root.title("Snipped Image Viewer")
    
    # Set up canvas to display the image
    canvas = tk.Canvas(root, width=image.width, height=image.height)
    canvas.pack()
    
    # Display the captured image
    photo = ImageTk.PhotoImage(image)
    canvas.create_image(0, 0, anchor="nw", image=photo)
    
    # Start the GUI main loop
    root.mainloop()

# Select area on the screen
def select_area():
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.config(bg="black")
    start_x = start_y = end_x = end_y = 0
    rect = None

    def on_mouse_down(event):
        nonlocal start_x, start_y, rect
        start_x = event.x_root
        start_y = event.y_root
        print(f"Mouse down at: ({event.x_root}, {event.y_root}) -> Start: ({start_x}, {start_y})")
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

    def on_mouse_drag(event):
        nonlocal rect, end_x, end_y
        end_x = event.x_root
        end_y = event.y_root
        print(f"Mouse drag at: ({event.x_root}, {event.y_root}) -> Current: ({end_x}, {end_y})")
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start_x, start_y, end_x, end_y, outline="red", width=2)

    def on_mouse_up(event):
        print(f"Mouse up at: ({event.x_root}, {event.y_root}) -> Final rectangle: ({start_x}, {start_y}, {end_x}, {end_y})")
        root.quit()
        root.destroy()
        capture_selected_area(start_x, start_y, end_x, end_y)

    canvas = tk.Canvas(root, cursor="cross")
    canvas.pack(fill="both", expand=True)
    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    root.mainloop()

# Tray icon setup
def on_exit(icon, item):
    icon.stop()
    sys.exit()

def run_tray():
    icon_image = PilImage.open("icon.ico")
    icon = pystray.Icon("NoBackgroundSnipper", icon_image, menu=pystray.Menu(item('Exit', on_exit)))
    icon.run()

# Start tray and set up hotkeys
if __name__ == "__main__":
    threading.Thread(target=run_tray, daemon=True).start()
    keyboard.add_hotkey("ctrl+alt+s", select_area)
    keyboard.add_hotkey("ctrl+alt+q", lambda: sys.exit())
    print("Running in the system tray. Press Ctrl+Alt+S to capture screen selection. Press Ctrl+Alt+Q to exit.")
    keyboard.wait("esc")
