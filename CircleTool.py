# CircleTool.py

import cv2
import numpy as np
from skimage.morphology import skeletonize
import threading
import time

def process_circle_area(x, y, open_cv_image, edge_mask, contours, circle_radius, gap_filling_level, handle_contour_coloring, history, update_canvas, remove_edges=False):
    mask = np.zeros(open_cv_image.shape[:2], dtype=np.uint8)
    cv2.circle(mask, (x, y), circle_radius - 4, 255, -1)

    region_edges = cv2.bitwise_and(edge_mask, mask) if edge_mask is not None else None
    if region_edges is None or not np.any(region_edges):
        return edge_mask, contours

    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    dilated_edges = cv2.dilate(region_edges, kernel, iterations=gap_filling_level)
    skeleton = skeletonize(dilated_edges > 0).astype(np.uint8) * 255

    if remove_edges:
        edge_mask = cv2.bitwise_and(edge_mask, cv2.bitwise_not(mask)) if edge_mask is not None else None
    else:
        edge_mask = cv2.bitwise_or(edge_mask, skeleton) if edge_mask is not None else skeleton

    contours, _ = cv2.findContours(edge_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    updated_image = handle_contour_coloring(open_cv_image.copy(), [], contours)

    history.append(updated_image.copy())
    update_canvas(updated_image)
    return edge_mask, contours

def draw_circle_cursor(event, canvas, circle_radius):
    canvas.delete("cursor_circle")
    x, y = event.x, event.y
    canvas.create_oval(x - circle_radius, y - circle_radius, x + circle_radius, y + circle_radius, outline="red", width=2, tags="cursor_circle")

def continuously_process_circle_area(event, process_circle_area, mouse_pressed, **kwargs):
    x, y = event.x, event.y

    def repeat_processing():
        while mouse_pressed.is_set():
            process_circle_area(x, y, **kwargs)
            time.sleep(0.1)
    threading.Thread(target=repeat_processing, daemon=True).start()

def on_circle_paint(event, mouse_pressed, **kwargs):
    mouse_pressed.set()
    process_circle_area(event.x, event.y, **kwargs)
    continuously_process_circle_area(event, process_circle_area, mouse_pressed, **kwargs)

def on_circle_paint_release(event, mouse_pressed):
    mouse_pressed.clear()

def on_circle_paint_right(event, **kwargs):
    process_circle_area(event.x, event.y, remove_edges=True, **kwargs)

def on_circle_paint_right_motion(event, **kwargs):
    process_circle_area(event.x, event.y, remove_edges=True, **kwargs)

def update_circle_radius(value, size_slider_value):
    global circle_radius
    circle_radius = int(float(value))
    size_slider_value.config(text=str(circle_radius))

def update_gap_filling_level(value, gap_filling_slider_value):
    global gap_filling_level
    gap_filling_level = int(float(value))
    gap_filling_slider_value.config(text=str(gap_filling_level))
