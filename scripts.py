import concurrent.futures
import threading
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageGrab, ImageFilter
import numpy as np
import cv2
from queue import LifoQueue
import keyboard
import pystray
from pystray import MenuItem as item
from io import BytesIO
import win32clipboard
from PIL import Image as PilImage  # For icon loading
import sys

# Define constants and global variables
DEFAULT_THRESHOLD = 100
INITIAL_THRESHOLD_RANGE = 30
RENDER_QUEUE = LifoQueue()  # Stack to store pre-rendered images
processed_images = {}  # Cache of processed images by threshold value
progress_count = 0  # Global counter for tracking progress

# Practical ranges for parameter combinations (simplified for performance)
threshold_values = list(range(50, 151, 10))
blur_values = [1, 2, 3]
edge_low_values = [20, 40, 60]
edge_high_values = [100, 120, 140]
morph_iterations = [1, 2]
grabcut_iterations = [2, 3]
total_combinations = len(threshold_values) * len(blur_values) * len(edge_low_values) * len(edge_high_values) * len(morph_iterations) * len(grabcut_iterations)

# Initial pre-rendering batch centered around the default threshold
initial_batch = [(th, blur_values[0], edge_low_values[0], edge_high_values[0], morph_iterations[0], grabcut_iterations[0])
                 for th in range(DEFAULT_THRESHOLD - INITIAL_THRESHOLD_RANGE,
                                 DEFAULT_THRESHOLD + INITIAL_THRESHOLD_RANGE + 1, 10)]

# Full combinations for background pre-rendering after the GUI is shown
combinations = [(th, bl, el, eh, mi, gi) for th in threshold_values for bl in blur_values 
                for el in edge_low_values for eh in edge_high_values 
                for mi in morph_iterations for gi in grabcut_iterations]

# Advanced background removal function
def advanced_background_removal(input_image, threshold, canny_threshold1, canny_threshold2, grabcut_iter):
    image = cv2.cvtColor(np.array(input_image), cv2.COLOR_RGBA2BGRA)
    
    # Ensure the image is in 3-channel BGR format for grabCut
    if image.shape[2] == 4:  # Check if the image has an alpha channel
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    original_image = image.copy()

    # Step 1: Gaussian Blur for Noise Reduction
    blurred = cv2.GaussianBlur(image, (3, 3), 0)

    # Step 2: Convert to HSV and apply Color Segmentation for mask creation
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    lower_bound = np.array([0, 0, threshold])  # Adjust based on slider input
    upper_bound = np.array([180, 255, 255])
    mask_hsv = cv2.inRange(hsv, lower_bound, upper_bound)

    # Step 3: Edge Detection using Canny with adjustable thresholds
    edges = cv2.Canny(blurred, canny_threshold1, canny_threshold2)
    _, mask_edges = cv2.threshold(edges, 1, 255, cv2.THRESH_BINARY)

    # Combine HSV and Edge-based masks for a refined mask
    combined_mask = cv2.bitwise_or(mask_hsv, mask_edges)

    # Step 4: Morphological Operations to refine the mask
    kernel = np.ones((3, 3), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=2)

    # Step 5: GrabCut refinement
    mask_grabcut = np.zeros(image.shape[:2], np.uint8)
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    rect = (5, 5, image.shape[1] - 10, image.shape[0] - 10)
    cv2.grabCut(original_image, mask_grabcut, rect, bg_model, fg_model, grabcut_iter, cv2.GC_INIT_WITH_RECT)
    mask_grabcut = np.where((mask_grabcut == 2) | (mask_grabcut == 0), 0, 1).astype("uint8")
    result = original_image * mask_grabcut[:, :, np.newaxis]

    # Convert result to RGBA with transparency where background is removed
    result_rgba = cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)
    result_rgba[:, :, 3] = (mask_grabcut * 255)  # Set alpha channel based on mask

    return PilImage.fromarray(result_rgba, "RGBA")

# Pre-render images for each combination
# Pre-render images for each combination
# Pre-render images for each combination
def pre_render_images(image, batch, all_combinations, progress_label, tuner_app):
    global progress_count
    progress_count = 0  # Initialize progress_count to zero

    def render_batch(batch, initial_display=False):
        global progress_count
        for params in batch:
            print(f"Rendering with parameters: {params}")
            processed_image = advanced_background_removal(image, *params[:4])
            processed_images[params[0]] = processed_image
            RENDER_QUEUE.put((params[0], processed_image))
            progress_count += 1

            # Update the progress label
            progress_label.config(text=f"Rendering Progress: {progress_count}/{total_combinations}")
            progress_label.update_idletasks()  # Ensure the label updates immediately

            # Display the first rendered image immediately
            if initial_display and progress_count == 1:
                tuner_app.update_image(params[0])

    # Render the initial batch and show the first image
    print("Starting initial batch rendering...")
    render_batch(batch, initial_display=True)
    print("Initial batch rendering completed.")

    # Continue rendering remaining combinations in the background
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(lambda params: render_batch([params]), all_combinations)

# Tuning GUI with slider and progress label
class BackgroundRemovalTuner:
    def __init__(self, root, image, progress_label):
        self.root = root
        self.image = image
        self.progress_label = progress_label  # Set the progress label

        # Set up GUI elements
        self.canvas = tk.Canvas(root, width=image.width, height=image.height)
        self.canvas.pack()
        
        # Slider for threshold adjustment
        self.threshold_slider = ttk.Scale(root, from_=DEFAULT_THRESHOLD - INITIAL_THRESHOLD_RANGE,
                                          to=DEFAULT_THRESHOLD + INITIAL_THRESHOLD_RANGE,
                                          orient="horizontal", command=self.on_slider_change)
        self.threshold_slider.pack()

        # Previous and Next buttons
        self.prev_button = tk.Button(root, text="<< Prev", command=self.show_prev_image)
        self.prev_button.pack(side=tk.LEFT)
        self.next_button = tk.Button(root, text="Next >>", command=self.show_next_image)
        self.next_button.pack(side=tk.RIGHT)
        
        self.photo = None  # Placeholder for the image display
        self.update_image(DEFAULT_THRESHOLD)  # Display the default threshold image

    def on_slider_change(self, event):
        threshold = int(self.threshold_slider.get())
        self.update_image(threshold)

    def show_prev_image(self):
        current_value = int(self.threshold_slider.get())
        new_value = max(self.threshold_slider.cget("from"), current_value - 1)
        self.threshold_slider.set(new_value)
        self.update_image(new_value)

    def show_next_image(self):
        current_value = int(self.threshold_slider.get())
        new_value = min(self.threshold_slider.cget("to"), current_value + 1)
        self.threshold_slider.set(new_value)
        self.update_image(new_value)

    def update_image(self, threshold):
        # Fetch pre-rendered image if available
        image = processed_images.get(threshold)
        if image:
            self.photo = ImageTk.PhotoImage(image)
            self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
            self.root.update()
        else:
            print(f"No pre-rendered image available for threshold: {threshold}")

# Display the tuning interface
def show_tuning_interface(image):
    root = tk.Tk()
    root.title("Background Removal Tuner")
    loading_label = tk.Label(root, text="Loading... Please wait")
    loading_label.pack()
    progress_label = tk.Label(root, text="Rendering Progress: 0/15000", font=("Arial", 10))
    progress_label.pack()
    tuner_app = BackgroundRemovalTuner(root, image, progress_label)
    root.after(100, lambda: loading_label.destroy())
    threading.Thread(target=pre_render_images, args=(image, initial_batch, combinations, progress_label)).start()
    root.mainloop()

# Capture selected area and show tuning interface
# Capture selected area and show tuning interface
# Capture selected area and show tuning interface
def capture_selected_area(x1, y1, x2, y2):
    # Grab the selected screen area
    image = ImageGrab.grab(bbox=(x1, y1, x2, y2)).convert("RGBA")
    
    # Initialize the GUI
    root = tk.Tk()
    root.title("Background Removal Tuner")
    
    # Create a progress label for tracking rendering progress
    progress_label = tk.Label(root, text="Rendering Progress: 0/15000")
    progress_label.pack()
    
    # Pass the progress_label to BackgroundRemovalTuner
    tuner_app = BackgroundRemovalTuner(root, image, progress_label)
    
    # Update the GUI and show the initial image as the GUI loads
    root.update()  
    
    # Start pre-rendering in a background thread
    threading.Thread(target=pre_render_images, args=(image, initial_batch, combinations, progress_label, tuner_app)).start()
    
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
        start_x, start_y = event.x, event.y
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

    def on_mouse_drag(event):
        nonlocal rect, end_x, end_y
        end_x, end_y = event.x, event.y
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start_x, start_y, end_x, end_y, outline="red", width=2)

    def on_mouse_up(event):
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

# Start tray, pre-render, and set up hotkeys
if __name__ == "__main__":
    threading.Thread(target=run_tray, daemon=True).start()
    keyboard.add_hotkey("ctrl+alt+s", select_area)
    keyboard.add_hotkey("ctrl+alt+q", lambda: sys.exit())
    print("Running in the system tray. Press Ctrl+Alt+S to capture screen selection and remove background. Press Ctrl+Alt+Q to exit.")
    keyboard.wait("esc")
