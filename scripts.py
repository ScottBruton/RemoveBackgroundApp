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
import tempfile
import io
import win32clipboard
from skimage.morphology import skeletonize  # For region growing and active contour approach

# Load environment variables
load_dotenv()

# Set DPI awareness to handle high DPI scaling
ctypes.windll.shcore.SetProcessDpiAwareness(2)

# Global list to store history of states for undo functionality
history = []

# Variable to adjust gap-filling level
gap_filling_level = 3  # You can adjust this value to control the intensity of gap-filling

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
    canvas = tk.Canvas(main_frame, width=image.width, height=image.height, scrollregion=(0, 0, image.width, image.height))
    hbar = tk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=canvas.xview)
    hbar.pack(side=tk.BOTTOM, fill=tk.X)
    vbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
    vbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
    canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    
    # Display the captured image
    photo = ImageTk.PhotoImage(image)
    canvas_image_id = canvas.create_image(0, 0, anchor="nw", image=photo)
    canvas.image = photo
    
    # Global variables to store object selections
    selected_objects = []
    edge_mask = None
    contours = []
    circle_radius = 20
    zoom_scale = 1.0
    pan_start_x = 0
    pan_start_y = 0
    tool_mode = None

    # Save the initial state to history for undo functionality
    history.append(open_cv_image.copy())

    # Function to update the canvas image
    def update_canvas(updated_image):
        highlighted_pil = PilImage.fromarray(cv2.cvtColor(updated_image, cv2.COLOR_BGR2RGB))
        highlighted_photo = ImageTk.PhotoImage(highlighted_pil)
        canvas.itemconfig(canvas_image_id, image=highlighted_photo)
        canvas.image = highlighted_photo

    # Function to handle contour coloring and selection
    def handle_contour_coloring(updated_image, selected_contours, all_contours):
        overlay = updated_image.copy()
        # Draw selected contours first with blue color
        for contour in selected_contours:
            color = (173, 216, 230)  # Baby blue for selected objects
            cv2.drawContours(overlay, [contour], -1, color, 2)
            if cv2.contourArea(contour) > 100:
                overlay_contour = overlay.copy()
                cv2.drawContours(overlay_contour, [contour], -1, color, thickness=cv2.FILLED)
                alpha = 0.4  # Higher alpha for selected contours
                cv2.addWeighted(overlay_contour, alpha, overlay, 1 - alpha, 0, overlay)
        # Draw non-selected contours with green color
        for contour in all_contours:
            if not any(np.array_equal(contour, selected) for selected in selected_contours):
                color = (0, 255, 0)  # Green for non-selected objects
                cv2.drawContours(overlay, [contour], -1, color, 2)
                if cv2.contourArea(contour) > 100:
                    overlay_contour = overlay.copy()
                    cv2.drawContours(overlay_contour, [contour], -1, color, thickness=cv2.FILLED)
                    alpha = 0.2  # Lower alpha for non-selected contours
                    cv2.addWeighted(overlay_contour, alpha, overlay, 1 - alpha, 0, overlay)
        return overlay

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
        nonlocal tool_mode
        tool_mode = "circle"
        canvas.config(cursor="none")  # Hide the default cursor
        size_slider_frame.pack(side=tk.RIGHT, fill=tk.Y)
        gap_filling_slider_frame.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.unbind("<Motion>")
        root.bind("<Motion>", draw_cursor_circle)  # Enable red circle cursor
        canvas.unbind("<ButtonPress-1>")
        canvas.unbind("<B1-Motion>")
        canvas.unbind("<ButtonRelease-1>")
        canvas.bind("<ButtonPress-1>", on_circle_paint)
        canvas.bind("<B1-Motion>", continuously_process_circle_area)
        canvas.bind("<ButtonRelease-1>", on_circle_paint_release)

    circle_tool_button = tk.Button(tools_panel, text="Circle Tool", command=select_circle_tool)
    circle_tool_button.pack(pady=10)

    # Add a vertical slider to control the circle size
    size_slider_frame = tk.Frame(root, width=100, bg="lightgrey")
    size_slider_label = tk.Label(size_slider_frame, text="Circle Size")
    size_slider_label.pack()
    size_slider_value = tk.Label(size_slider_frame, text=str(circle_radius))
    size_slider_value.pack()
    def update_circle_radius(value):
        nonlocal circle_radius
        circle_radius = int(float(value))
        size_slider_value.config(text=str(circle_radius))
    size_slider = ttk.Scale(size_slider_frame, from_=5, to=100, orient="vertical", command=lambda v: update_circle_radius(v))
    size_slider.set(circle_radius)
    size_slider.pack()

    # Add a vertical slider to control the gap filling level
    gap_filling_slider_frame = tk.Frame(root, width=100, bg="lightgrey")
    gap_filling_slider_label = tk.Label(gap_filling_slider_frame, text="Gap Filling Level")
    gap_filling_slider_label.pack()
    gap_filling_slider_value = tk.Label(gap_filling_slider_frame, text=str(gap_filling_level))
    gap_filling_slider_value.pack()
    def update_gap_filling_level(value):
        global gap_filling_level
        gap_filling_level = int(float(value))
        gap_filling_slider_value.config(text=str(gap_filling_level))
    gap_filling_slider = ttk.Scale(gap_filling_slider_frame, from_=1, to=10, orient="vertical", command=lambda v: update_gap_filling_level(v))
    gap_filling_slider.set(gap_filling_level)
    gap_filling_slider.pack()

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
        edge_highlight = handle_contour_coloring(open_cv_image.copy(), selected_objects, contours)
        
        # Save the state to history
        history.append(edge_highlight.copy())
        
        # Update the canvas with the highlighted image
        update_canvas(edge_highlight)
        extract_button.config(state="normal")  # Re-enable the button after processing
    
    def process_circle_area(x, y, remove_edges=False):
        nonlocal edge_mask, contours
        # Define the circular region of interest
        mask = np.zeros(open_cv_image.shape[:2], dtype=np.uint8)
        cv2.circle(mask, (x, y), circle_radius - 4, 255, -1)
        
        # Extract the region below the circle
        region_edges = cv2.bitwise_and(edge_mask, mask) if edge_mask is not None else None
        if region_edges is None or not np.any(region_edges):
            # If there are no edges in the selected region, do nothing
            return
        
        # Apply morphological dilation to bridge gaps within the selected region using a cross-shaped kernel
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))  # Cross-shaped kernel for better control of growth direction
        dilated_edges = cv2.dilate(region_edges, kernel, iterations=gap_filling_level)
        
        # Use active contour refinement
        # Skeletonize the region to refine the edges
        skeleton = skeletonize(dilated_edges > 0).astype(np.uint8) * 255
        
        if remove_edges:
            # Remove edges within the circular region
            edge_mask = cv2.bitwise_and(edge_mask, cv2.bitwise_not(mask)) if edge_mask is not None else None
        else:
            # Update edge mask with processed edges
            edge_mask = cv2.bitwise_or(edge_mask, skeleton) if edge_mask is not None else skeleton
        
        # Update contours after processing or removal
        contours, _ = cv2.findContours(edge_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Update the display with the newly processed area
        updated_image = handle_contour_coloring(open_cv_image.copy(), selected_objects, contours)
        
        # Save the state to history
        history.append(updated_image.copy())
        
        # Update the canvas
        update_canvas(updated_image)

    def continuously_process_circle_area(event):
        x, y = event.x, event.y
        def repeat_processing():
            while mouse_pressed:
                process_circle_area(x, y)
                time.sleep(0.5)  # Repeat every 0.5 seconds
        threading.Thread(target=repeat_processing, daemon=True).start()

    mouse_pressed = False

    def on_circle_paint(event):
        nonlocal mouse_pressed
        mouse_pressed = True
        process_circle_area(event.x, event.y)
        continuously_process_circle_area(event)

    def on_circle_paint_release(event):
        nonlocal mouse_pressed
        mouse_pressed = False

    def on_circle_paint_right(event):
        x, y = event.x, event.y
        process_circle_area(x, y, remove_edges=True)

    def on_circle_paint_right_motion(event):
        x, y = event.x, event.y
        process_circle_area(x, y, remove_edges=True)

    # Draw the initial cursor circle only if the tool is selected
    def draw_cursor_circle(event):
        if tool_mode == "circle":  # Only draw if the circle tool is active
            canvas.delete("cursor_circle")
            canvas.create_oval(event.x - circle_radius, event.y - circle_radius, event.x + circle_radius, event.y + circle_radius, outline="red", width=2, tags="cursor_circle")

    # Add zoom functionality
    def zoom(event):
        nonlocal zoom_scale, photo
        if event.delta > 0:  # Scroll up to zoom in
            zoom_scale *= 1.1
        elif event.delta < 0 and zoom_scale > 1.0:  # Scroll down to zoom out, but not below original size
            zoom_scale /= 1.1
        
        # Get the cursor position and calculate the offset
        cursor_x, cursor_y = canvas.canvasx(event.x), canvas.canvasy(event.y)
        zoomed_image = cv2.resize(open_cv_image, None, fx=zoom_scale, fy=zoom_scale, interpolation=cv2.INTER_LINEAR)
        
        # Calculate new position to keep cursor at the same relative point
        new_width, new_height = zoomed_image.shape[1], zoomed_image.shape[0]
        offset_x = max(0, min(new_width - canvas.winfo_width(), int(cursor_x * zoom_scale - event.x)))
        offset_y = max(0, min(new_height - canvas.winfo_height(), int(cursor_y * zoom_scale - event.y)))
        canvas.config(scrollregion=(0, 0, new_width, new_height))
        canvas.xview_moveto(offset_x / new_width)
        canvas.yview_moveto(offset_y / new_height)
        
        highlighted_pil = PilImage.fromarray(cv2.cvtColor(zoomed_image, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(highlighted_pil)
        canvas.itemconfig(canvas_image_id, image=photo)
        canvas.image = photo
        # Ensure contours are also updated in zoom state
        update_canvas(zoomed_image)

    canvas.bind("<MouseWheel>", zoom)
    
    # Panning functionality
    def start_pan(event):
        nonlocal pan_start_x, pan_start_y
        pan_start_x = event.x
        pan_start_y = event.y

    def pan_image(event):
        dx = event.x - pan_start_x
        dy = event.y - pan_start_y
        canvas.xview_scroll(-dx, "units")
        canvas.yview_scroll(-dy, "units")
        pan_start_x = event.x
        pan_start_y = event.y

    canvas.bind("<ButtonPress-2>", start_pan)  # Middle mouse button to start panning
    canvas.bind("<B2-Motion>", pan_image)  # Hold and move the middle mouse button to pan
    
    extract_button = tk.Button(root, text="Extract Objects", command=extract_objects)
    extract_button.pack()

    # Add "Select Objects" button
    def select_objects():
        nonlocal tool_mode
        tool_mode = "select"
        canvas.config(cursor="arrow")
        size_slider_frame.pack_forget()
        gap_filling_slider_frame.pack_forget()
        canvas.unbind("<Motion>")
        canvas.delete("cursor_circle")
        
        def on_hover(event):
            x, y = event.x, event.y
            for contour in contours:
                if cv2.pointPolygonTest(contour, (x, y), False) >= 0:
                    canvas.config(cursor="hand2")
                    return
            canvas.config(cursor="arrow")

        def on_click(event):
            nonlocal selected_objects
            x, y = event.x, event.y
            for contour in contours:
                if cv2.pointPolygonTest(contour, (x, y), False) >= 0:
                    if not any(np.array_equal(contour, selected) for selected in selected_objects):
                        selected_objects.append(contour)
                        update_copy_button_state()
                        update_selected_objects()
                    return

        def on_right_click(event):
            nonlocal selected_objects
            x, y = event.x, event.y
            for contour in selected_objects:
                if cv2.pointPolygonTest(contour, (x, y), False) >= 0:
                    selected_objects = [c for c in selected_objects if not np.array_equal(c, contour)]
                    update_copy_button_state()
                    update_selected_objects()
                    return

        canvas.bind("<Motion>", on_hover)
        canvas.bind("<ButtonPress-1>", on_click)
        canvas.bind("<ButtonPress-3>", on_right_click)

    def update_selected_objects():
        updated_image = handle_contour_coloring(open_cv_image.copy(), selected_objects, contours)
        update_canvas(updated_image)

    select_objects_button = tk.Button(tools_panel, text="Select Objects", command=select_objects)
    select_objects_button.pack(pady=10)

    # Add "Copy Objects" button
    def copy_objects():
        if not selected_objects:
            return
        # Create an empty transparent image
        copied_image = np.zeros((open_cv_image.shape[0], open_cv_image.shape[1], 4), dtype=np.uint8)
        for contour in selected_objects:
            mask = np.zeros_like(open_cv_image[:, :, 0], dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)
            # Copy RGB channels from the original image
            for c in range(3):
                copied_image[:, :, c] = cv2.bitwise_and(open_cv_image[:, :, c], open_cv_image[:, :, c], mask=mask)
            # Set alpha channel based on mask
            copied_image[:, :, 3] = mask
        output = PilImage.fromarray(copied_image, 'RGBA')
        output_buffer = io.BytesIO()
        output.save(output_buffer, format='BMP')
        data = output_buffer.getvalue()[14:]
        output_buffer.close()

        # Set the image to clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    copy_button = tk.Button(tools_panel, text="Copy Objects", command=copy_objects, state="disabled")
    copy_button.pack(pady=10)

    def update_copy_button_state():
        if selected_objects:
            copy_button.config(state="normal")
        else:
            copy_button.config(state="disabled")

    # Add "Exit" button to close the application
    def exit_application():
        root.quit()
        root.destroy()
        os._exit(0)  # Forcefully terminate the program

    exit_button = tk.Button(tools_panel, text="Exit", command=exit_application)
    exit_button.pack(pady=10)

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
    os._exit(0)  # Forcefully terminate the program

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
    keyboard.add_hotkey("ctrl+alt+q", lambda: os._exit(0))  # Forcefully terminate the program
    print("Running in the system tray. Press Ctrl+Alt+S to capture screen selection. Press Ctrl+Alt+Q to exit.")
    keyboard.wait("esc")
