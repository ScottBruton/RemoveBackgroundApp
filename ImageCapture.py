# ImageCapture.py
import tkinter as tk
from PIL import ImageGrab
from GUIElements import setup_gui  # This is where setup_gui is defined to display the main app GUI

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
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

    def on_mouse_drag(event):
        nonlocal rect, end_x, end_y
        end_x = event.x_root
        end_y = event.y_root
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start_x, start_y, end_x, end_y, outline="red", width=2)

    def on_mouse_up(event):
        nonlocal start_x, start_y, end_x, end_y
        root.quit()
        root.destroy()
        # Capture the selected screen area
        captured_image = capture_selected_area(start_x, start_y, end_x, end_y)
        if captured_image:
            setup_gui(captured_image)  # Initialize GUI with the captured image

    def capture_selected_area(x1, y1, x2, y2):
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        try:
            # Capture and return the selected area
            image = ImageGrab.grab(bbox=(x1, y1, x2, y2)).convert("RGBA")
            return image
        except Exception as e:
            print("Error capturing selected area:", e)
            return None

    canvas = tk.Canvas(root, cursor="cross")
    canvas.pack(fill="both", expand=True)
    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    root.mainloop()
