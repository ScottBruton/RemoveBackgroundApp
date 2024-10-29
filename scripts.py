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
import cv2
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    
    # Convert the image to an OpenCV format
    open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGR)
    
    # Initialize the GUI
    root = tk.Tk()
    root.title("Snipped Image Viewer")
    
    # Set up canvas to display the image
    canvas = tk.Canvas(root, width=image.width, height=image.height)
    canvas.pack()
    
    # Display the captured image
    photo = ImageTk.PhotoImage(image)
    canvas.create_image(0, 0, anchor="nw", image=photo)
    
    # Add "Extract Objects" button below the image
    def extract_objects():
        print("Extract Objects button clicked")
        extract_button.config(state="disabled")  # Disable the button during processing
        
        # Step 1: Bilateral Filter + Gaussian Blur + Edge Detection (Canny) + Thresholding
        bilateral_filtered = cv2.bilateralFilter(open_cv_image, 9, 75, 75)  # Preserve edges while reducing noise
        blurred = cv2.GaussianBlur(bilateral_filtered, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 100)  # Adjusted thresholds for better edge detection
        _, thresh = cv2.threshold(edges, 127, 255, cv2.THRESH_BINARY)
        
        # Step 2: Color Segmentation (HSV Filtering) + Morphological Operations
        hsv = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2HSV)
        lower_bound = np.array([0, 0, 0])
        upper_bound = np.array([180, 255, 255])
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))  # Increased kernel size for better noise removal
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)  # Closing gaps
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)  # Removing small noise
        
        # Step 3: Watershed Algorithm with Marker-based Segmentation
        dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        _, fg = cv2.threshold(dist_transform, 0.6 * dist_transform.max(), 255, 0)
        fg = np.uint8(fg)
        unknown = cv2.subtract(mask, fg)
        _, markers = cv2.connectedComponents(fg)
        markers = markers + 1
        markers[unknown == 255] = 0
        markers = cv2.watershed(open_cv_image, markers)
        open_cv_image[markers == -1] = [0, 255, 0]
        
        # Step 4: Final Refinement with GrabCut
        rect = (10, 10, open_cv_image.shape[1] - 20, open_cv_image.shape[0] - 20)  # Define a rectangle for GrabCut
        mask_init = np.zeros(open_cv_image.shape[:2], np.uint8)
        mask_init[markers == 1] = cv2.GC_PR_FGD
        mask_init[markers == 0] = cv2.GC_PR_BGD
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        cv2.grabCut(open_cv_image, mask_init, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        mask_final = np.where((mask_init == 2) | (mask_init == 0), 0, 1).astype('uint8')
        result = open_cv_image * mask_final[:, :, np.newaxis]
        
        # Convert back to PIL format for Tkinter
        highlighted_pil = PilImage.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        highlighted_photo = ImageTk.PhotoImage(highlighted_pil)
        
        # Update the canvas with the highlighted image
        canvas.create_image(0, 0, anchor="nw", image=highlighted_photo)
        canvas.image = highlighted_photo
        
        extract_button.config(state="normal")  # Re-enable the button after processing
        
    extract_button = tk.Button(root, text="Extract Objects", command=extract_objects)
    extract_button.pack()
    
    # Start the GUI main loop
    root.mainloop()

# Select area on the screen
def select_area():
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.config(bg="black")
    root.after(10, lambda: root.focus_force())  # Bring the window to the foreground after a short delay
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
    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()
    time.sleep(1)  # Wait for the tray icon to initialize properly
    keyboard.add_hotkey("ctrl+alt+s", select_area)
    keyboard.add_hotkey("ctrl+alt+q", lambda: sys.exit())
    print("Running in the system tray. Press Ctrl+Alt+S to capture screen selection. Press Ctrl+Alt+Q to exit.")
    keyboard.wait("esc")
