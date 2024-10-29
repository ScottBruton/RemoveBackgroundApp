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
    canvas.image = photo
    
    # Global variables to store object selections
    selected_objects = []
    edge_mask = None
    contours = []
    gap_start_x = gap_start_y = 0
    gap_rect = None

    # Add "Extract Objects" button below the image
    def extract_objects():
        nonlocal edge_mask, contours
        print("Extract Objects button clicked")
        extract_button.config(state="disabled")  # Disable the button during processing
        
        # Step 1: Bilateral Filter + Gaussian Blur + Edge Detection (Canny) + Thresholding
        bilateral_filtered = cv2.bilateralFilter(open_cv_image, 9, 75, 75)  # Preserve edges while reducing noise
        blurred = cv2.GaussianBlur(bilateral_filtered, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 100)  # Adjusted thresholds for better edge detection
        
        # Store the edge mask for later use in selecting objects
        edge_mask = edges
        
        # Find contours from the edge mask
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Create an edge overlay on the original image
        edge_highlight = open_cv_image.copy()
        cv2.drawContours(edge_highlight, contours, -1, (0, 255, 0), 2)  # Highlight edges in green
        
        # Convert back to PIL format for Tkinter
        highlighted_pil = PilImage.fromarray(cv2.cvtColor(edge_highlight, cv2.COLOR_BGR2RGB))
        highlighted_photo = ImageTk.PhotoImage(highlighted_pil)
        
        # Update the canvas with the highlighted image
        canvas.create_image(0, 0, anchor="nw", image=highlighted_photo)
        canvas.image = highlighted_photo
        
        extract_button.config(state="normal")  # Re-enable the button after processing
    
    def close_gap(x1, y1, x2, y2):
        # Process the area of the gap to close it using the edge detection algorithm
        nonlocal edge_mask, contours
        gap_area = open_cv_image[y1:y2, x1:x2]
        blurred = cv2.GaussianBlur(gap_area, (5, 5), 0)
        edges_local = cv2.Canny(blurred, 30, 100)
        edge_mask[y1:y2, x1:x2] = edges_local
        
        # Update contours after closing the gap
        contours, _ = cv2.findContours(edge_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Update the display with the newly closed gap
        updated_image = open_cv_image.copy()
        for obj in selected_objects:
            cv2.drawContours(updated_image, [obj], -1, (255, 182, 193), 2)  # Highlight selected objects in bright baby blue
        for contour in contours:
            if contour not in selected_objects:
                cv2.drawContours(updated_image, [contour], -1, (0, 255, 0), 2)  # Highlight non-selected objects in green
        
        # Convert to PIL format and update canvas
        highlighted_pil = PilImage.fromarray(cv2.cvtColor(updated_image, cv2.COLOR_BGR2RGB))
        highlighted_photo = ImageTk.PhotoImage(highlighted_pil)
        canvas.create_image(0, 0, anchor="nw", image=highlighted_photo)
        canvas.image = highlighted_photo
    
    def on_gap_selection(event):
        nonlocal gap_start_x, gap_start_y, gap_rect
        gap_start_x = event.x
        gap_start_y = event.y
        gap_rect = canvas.create_rectangle(gap_start_x, gap_start_y, gap_start_x, gap_start_y, outline="grey", width=2)
    
    def on_gap_drag(event):
        nonlocal gap_rect
        gap_end_x, gap_end_y = event.x, event.y
        canvas.coords(gap_rect, gap_start_x, gap_start_y, gap_end_x, gap_end_y)
    
    def on_gap_release(event):
        nonlocal gap_start_x, gap_start_y, gap_rect
        gap_end_x, gap_end_y = event.x, event.y
        canvas.delete(gap_rect)
        gap_x1, gap_x2 = min(gap_start_x, gap_end_x), max(gap_start_x, gap_end_x)
        gap_y1, gap_y2 = min(gap_start_y, gap_end_y), max(gap_start_y, gap_end_y)
        close_gap(gap_x1, gap_y1, gap_x2, gap_y2)
    
    def on_remove_edges_selection(event):
        nonlocal gap_start_x, gap_start_y, gap_rect
        gap_start_x = event.x
        gap_start_y = event.y
        gap_rect = canvas.create_rectangle(gap_start_x, gap_start_y, gap_start_x, gap_start_y, outline="red", width=2)
    
    def on_remove_edges_drag(event):
        nonlocal gap_rect
        gap_end_x, gap_end_y = event.x, event.y
        canvas.coords(gap_rect, gap_start_x, gap_start_y, gap_end_x, gap_end_y)
    
    def on_remove_edges_release(event):
        nonlocal gap_start_x, gap_start_y, gap_rect, contours, edge_mask
        gap_end_x, gap_end_y = event.x, event.y
        canvas.delete(gap_rect)
        gap_x1, gap_x2 = min(gap_start_x, gap_end_x), max(gap_start_x, gap_end_x)
        gap_y1, gap_y2 = min(gap_start_y, gap_end_y), max(gap_start_y, gap_end_y)
        
        # Remove edges within the selected rectangle
        edge_mask[gap_y1:gap_y2, gap_x1:gap_x2] = 0
        
        # Update contours after removing edges
        contours, _ = cv2.findContours(edge_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Update the display with the newly removed edges
        updated_image = open_cv_image.copy()
        for obj in selected_objects:
            cv2.drawContours(updated_image, [obj], -1, (255, 182, 193), 2)  # Highlight selected objects in bright baby blue
        for contour in contours:
            if contour not in selected_objects:
                cv2.drawContours(updated_image, [contour], -1, (0, 255, 0), 2)  # Highlight non-selected objects in green
        
        # Convert to PIL format and update canvas
        highlighted_pil = PilImage.fromarray(cv2.cvtColor(updated_image, cv2.COLOR_BGR2RGB))
        highlighted_photo = ImageTk.PhotoImage(highlighted_pil)
        canvas.create_image(0, 0, anchor="nw", image=highlighted_photo)
        canvas.image = highlighted_photo
    
    canvas.bind("<ButtonPress-1>", on_gap_selection)  # Left click to start selecting a gap
    canvas.bind("<B1-Motion>", on_gap_drag)  # Drag to select the area of the gap
    canvas.bind("<ButtonRelease-1>", on_gap_release)  # Release to close the gap
    
    canvas.bind("<ButtonPress-3>", on_remove_edges_selection)  # Right click to start selecting an area to remove edges
    canvas.bind("<B3-Motion>", on_remove_edges_drag)  # Drag to select the area to remove edges
    canvas.bind("<ButtonRelease-3>", on_remove_edges_release)  # Release to remove edges
    
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
