# GUIElements.py

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import cv2
import numpy as np
from appState import history, selected_objects, circle_radius, gap_filling_level
from ImageProcessing import extract_objects, handle_contour_coloring
from ClipboardManager import copy_objects_to_clipboard
from CircleTool import (
    process_circle_area, draw_circle_cursor, continuously_process_circle_area,
    on_circle_paint, on_circle_paint_release, on_circle_paint_right,
    on_circle_paint_right_motion, update_circle_radius, update_gap_filling_level
)

# Initialize mouse_pressed as a threading.Event for click-and-drag functionality
mouse_pressed = threading.Event()

def setup_gui(image):
    # Convert the PIL image to OpenCV format
    open_cv_image = np.array(image.convert("RGB"))[:, :, ::-1]
    history.append(open_cv_image.copy())

    root = tk.Tk()
    root.title("Snipped Image Viewer")

    main_frame = tk.Frame(root)
    main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tools_panel = tk.Frame(main_frame, width=100, bg="lightgrey")
    tools_panel.pack(side=tk.LEFT, fill=tk.Y)

    canvas = tk.Canvas(main_frame, width=open_cv_image.shape[1], height=open_cv_image.shape[0],
                       scrollregion=(0, 0, open_cv_image.shape[1], open_cv_image.shape[0]))
    hbar = tk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=canvas.xview)
    hbar.pack(side=tk.BOTTOM, fill=tk.X)
    vbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
    vbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
    canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    pil_image = Image.fromarray(cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2RGB))
    photo_image = ImageTk.PhotoImage(pil_image)
    canvas_image_id = canvas.create_image(0, 0, anchor="nw", image=photo_image)
    canvas.image = photo_image

    def update_canvas(new_image):
        pil_image = Image.fromarray(new_image)
        photo_image = ImageTk.PhotoImage(pil_image)
        canvas.itemconfig(canvas_image_id, image=photo_image)
        canvas.image = photo_image

    def undo_last_action():
        if len(history) > 1:
            history.pop()
            previous_state = history[-1]
            update_canvas(previous_state)

    undo_button = tk.Button(tools_panel, text="Undo", command=undo_last_action)
    undo_button.pack(pady=10)

    def on_extract_objects():
        edge_mask, contours = extract_objects(open_cv_image)
        highlighted_image = handle_contour_coloring(open_cv_image.copy(), selected_objects, contours)
        history.append(highlighted_image.copy())
        update_canvas(highlighted_image)

    extract_button = tk.Button(tools_panel, text="Extract Objects", command=on_extract_objects)
    extract_button.pack(pady=10)

    def activate_circle_tool():
        canvas.config(cursor="none")
        size_slider_frame.pack(side=tk.RIGHT, fill=tk.Y)
        gap_filling_slider_frame.pack(side=tk.RIGHT, fill=tk.Y)
        mouse_pressed.clear()

        canvas.bind("<Motion>", lambda event: draw_circle_cursor(event, canvas, circle_radius))
        canvas.bind("<ButtonPress-1>", lambda event: on_circle_paint(
            event, mouse_pressed, open_cv_image=open_cv_image, edge_mask=None, contours=[],
            circle_radius=circle_radius, gap_filling_level=gap_filling_level,
            handle_contour_coloring=handle_contour_coloring, history=history, update_canvas=update_canvas
        ))
        canvas.bind("<B1-Motion>", lambda event: continuously_process_circle_area(
            event, process_circle_area, open_cv_image=open_cv_image, edge_mask=None, contours=[],
            circle_radius=circle_radius, gap_filling_level=gap_filling_level,
            handle_contour_coloring=handle_contour_coloring, history=history,
            update_canvas=update_canvas, mouse_pressed=mouse_pressed
        ))
        canvas.bind("<ButtonRelease-1>", lambda event: on_circle_paint_release(event, mouse_pressed))
        canvas.bind("<ButtonPress-3>", lambda event: on_circle_paint_right(
            event, open_cv_image=open_cv_image, edge_mask=None, contours=[], circle_radius=circle_radius,
            gap_filling_level=gap_filling_level, handle_contour_coloring=handle_contour_coloring,
            history=history, update_canvas=update_canvas
        ))
        canvas.bind("<B3-Motion>", lambda event: on_circle_paint_right_motion(
            event, open_cv_image=open_cv_image, edge_mask=None, contours=[], circle_radius=circle_radius,
            gap_filling_level=gap_filling_level, handle_contour_coloring=handle_contour_coloring,
            history=history, update_canvas=update_canvas
        ))

    circle_tool_button = tk.Button(tools_panel, text="Circle Tool", command=activate_circle_tool)
    circle_tool_button.pack(pady=10)

    size_slider_frame = tk.Frame(root, width=100, bg="lightgrey")
    size_slider_label = tk.Label(size_slider_frame, text="Circle Size")
    size_slider_label.pack()
    size_slider_value = tk.Label(size_slider_frame, text=str(circle_radius))
    size_slider_value.pack()
    size_slider = ttk.Scale(size_slider_frame, from_=5, to=100, orient="vertical",
                            command=lambda v: update_circle_radius(v, size_slider_value))
    size_slider.set(circle_radius)
    size_slider.pack()

    gap_filling_slider_frame = tk.Frame(root, width=100, bg="lightgrey")
    gap_filling_slider_label = tk.Label(gap_filling_slider_frame, text="Gap Filling Level")
    gap_filling_slider_label.pack()
    gap_filling_slider_value = tk.Label(gap_filling_slider_frame, text=str(gap_filling_level))
    gap_filling_slider_value.pack()
    gap_filling_slider = ttk.Scale(gap_filling_slider_frame, from_=1, to=10, orient="vertical",
                                   command=lambda v: update_gap_filling_level(v, gap_filling_slider_value))
    gap_filling_slider.set(gap_filling_level)
    gap_filling_slider.pack()

    def exit_application():
        root.quit()
        root.destroy()

    exit_button = tk.Button(tools_panel, text="Exit", command=exit_application)
    exit_button.pack(pady=10)

    root.mainloop()
