import threading
import tkinter as tk
from tkinter import ttk
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

# Global list to store history of states for undo functionality
history = []

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
    
    # Set up main frame with a vertical panel on the left
    main_frame = tk.Frame(root)
    main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tools_panel = tk.Frame(main_frame, width=100, bg="lightgrey")
    tools_panel.pack(side=tk.LEFT, fill=tk.Y)

    # Set up canvas to display the image
    canvas = tk.Canvas(main_frame, width=image.width, height=image.height)
    canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    # Display the captured image
    photo = ImageTk.PhotoImage(image)
    canvas.create_image(0, 0, anchor="nw", image=photo)
    canvas.image = photo
    
    # Global variables to store object selections
    selected_objects = []
    edge_mask = None
    contours = []
    circle_radius = 20

    # Save the initial state to history for undo functionality
    history.append(open_cv_image.copy())

    # Function to update the canvas image
    def update_canvas(updated_image):
        highlighted_pil = PilImage.fromarray(cv2.cvtColor(updated_image, cv2.COLOR_BGR2RGB))
        highlighted_photo = ImageTk.PhotoImage(highlighted_pil)
        canvas.create_image(0, 0, anchor="nw", image=highlighted_photo)
        canvas.image = highlighted_photo

    # Undo functionality
    def undo_last_action():
        if len(history) > 1:
            history.pop()  # Remove the last action
            previous_state = history[-1]
            update_canvas(previous_state)

    # Add an Undo button to the tools panel
    undo_button = tk.Button(tools_panel, text="Undo", command=undo_last_action)
    undo_button.pack(pady=10)

    # Tool selection for circular processing
    def select_circle_tool():
        canvas.config(cursor="none")  # Hide the default cursor
        size_slider_frame.pack(side=tk.RIGHT, fill=tk.Y)
        root.bind("<Motion>", draw_cursor_circle)  # Enable red circle cursor

    circle_tool_button = tk.Button(tools_panel, text="Circle Tool", command=select_circle_tool)
    circle_tool_button.pack(pady=10)

    # Add a vertical slider to control the circle size
    size_slider_frame = tk.Frame(root, width=100, bg="lightgrey")
    size_slider_label = tk.Label(size_slider_frame, text="Circle Size")
    size_slider_label.pack()
    def update_circle_radius(value):
        nonlocal circle_radius
        circle_radius = value
    size_slider = ttk.Scale(size_slider_frame, from_=5, to=100, orient="vertical", command=lambda v: update_circle_radius(int(float(v))))
    size_slider.set(circle_radius)
    size_slider.pack()

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
        for contour in contours:
            cv2.drawContours(edge_highlight, [contour], -1, (0, 255, 0), 2)  # Highlight edges in green
            if cv2.contourArea(contour) > 0:  # Check if contour forms a closed shape
                overlay = np.zeros_like(open_cv_image, dtype=np.uint8)
                cv2.drawContours(overlay, [contour], -1, (0, 255, 0), -1)  # Fill closed contours with green
                alpha = 0.3  # Transparency factor
                edge_highlight = cv2.addWeighted(overlay, alpha, edge_highlight, 1 - alpha, 0)
        
        # Save the state to history
        history.append(edge_highlight.copy())
        
        # Update the canvas with the highlighted image
        update_canvas(edge_highlight)
        extract_button.config(state="normal")  # Re-enable the button after processing
    
    def process_circle_area(x, y):
        nonlocal edge_mask, contours
        # Define the circular region of interest
        mask = np.zeros(open_cv_image.shape[:2], dtype=np.uint8)
        cv2.circle(mask, (x, y), circle_radius, 255, -1)
        
        # Extract the region and process it
        region = cv2.bitwise_and(open_cv_image, open_cv_image, mask=mask)
        blurred = cv2.GaussianBlur(region, (5, 5), 0)
        edges_local = cv2.Canny(blurred, 30, 100)
        if np.any(edges_local):  # Only proceed if there are edges detected in the region
            edge_mask = cv2.bitwise_or(edge_mask, edges_local) if edge_mask is not None else edges_local
            
            # Update contours after processing
            contours, _ = cv2.findContours(edge_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Update the display with the newly processed area
            updated_image = open_cv_image.copy()
            for contour in contours:
                cv2.drawContours(updated_image, [contour], -1, (0, 255, 0), 2)  # Highlight edges in green
                if cv2.contourArea(contour) > 0:  # Check if contour forms a closed shape
                    overlay = np.zeros_like(open_cv_image, dtype=np.uint8)
                    cv2.drawContours(overlay, [contour], -1, (0, 255, 0), -1)  # Fill closed contours with transparent green
                    alpha = 0.3  # Transparency factor
                    updated_image = cv2.addWeighted(overlay, alpha, updated_image, 1 - alpha, 0)
            
            # Save the state to history
            history.append(updated_image.copy())
            
            # Update the canvas
            update_canvas(updated_image)

    def on_circle_paint(event):
        x, y = event.x, event.y
        process_circle_area(x, y)
        # Draw a circle cursor to indicate the current brush size
        canvas.delete("cursor_circle")
        canvas.create_oval(x - circle_radius, y - circle_radius, x + circle_radius, y + circle_radius, outline="red", width=2, tags="cursor_circle")

    def on_circle_paint_end(event):
        # Remove the circle cursor when mouse button is released
        canvas.delete("cursor_circle")

    # Bind mouse events to canvas for the circular tool
    canvas.bind("<ButtonPress-1>", on_circle_paint)  # Left click to start processing
    canvas.bind("<B1-Motion>", on_circle_paint)  # Drag to process continuously
    canvas.bind("<ButtonRelease-1>", on_circle_paint_end)  # Remove circle cursor on release
    
    # Draw the initial cursor circle only if the tool is selected
    def draw_cursor_circle(event):
        if size_slider_frame.winfo_ismapped():  # Only draw if the circle tool is active
            canvas.delete("cursor_circle")
            canvas.create_oval(event.x - circle_radius, event.y - circle_radius, event.x + circle_radius, event.y + circle_radius, outline="red", width=2, tags="cursor_circle")

    canvas.bind("<Motion>", draw_cursor_circle)
    
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
