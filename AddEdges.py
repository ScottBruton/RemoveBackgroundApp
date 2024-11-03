import cv2
import appState
import numpy as np

class AddEdges:
    def __init__(self, root, canvas, open_cv_image, update_canvas, history, selected_edges):
        self.root = root
        self.canvas = canvas
        self.open_cv_image = open_cv_image
        self.update_canvas = update_canvas
        self.history = history
        self.selected_edges = selected_edges
        self.paint_radius = 10  # Default radius for painting
        self.overlay = None
        self.paint_mask = np.zeros((open_cv_image.shape[0], open_cv_image.shape[1]), dtype=np.uint8)
        self.last_x = None
        self.last_y = None

    def select_add_edges_tool(self):
        # Set up the canvas to use the paint tool
        self.canvas.bind("<ButtonPress-1>", self.on_paint_start)
        self.canvas.bind("<B1-Motion>", self.on_paint)
        self.canvas.bind("<ButtonRelease-1>", self.on_paint_end)

        # Retrieve the overlay from appState and set it to self.overlay
        self.overlay = appState.get_overlay()
        if self.overlay is None:
            self.overlay = self.open_cv_image.copy()

    def on_paint_start(self, event):
        # Start painting
        self.last_x, self.last_y = event.x, event.y
        self.paint_path(event.x, event.y)

    def on_paint(self, event):
        # Continue painting while the mouse is pressed
        self.paint_path(event.x, event.y)
        self.last_x, self.last_y = event.x, event.y

    def on_paint_end(self, event):
        # Save the painted path to the appState overlay
        appState.save_overlay(self.overlay)
        # Save the current state to history for undo functionality
        self.history.append(self.overlay.copy())
        # Reset the last position
        self.last_x, self.last_y = None, None

    def paint_path(self, x, y):
        if self.last_x is None or self.last_y is None:
            # If there is no previous point, just mark the current point
            cv2.circle(self.paint_mask, (x, y), self.paint_radius, 1, -1)
            temp_overlay = self.overlay.copy()
            cv2.circle(temp_overlay, (x, y), self.paint_radius, (255, 0, 255), -1)  # Purple color
        else:
            # Draw a line between the last point and the current point
            cv2.line(self.paint_mask, (self.last_x, self.last_y), (x, y), 1, self.paint_radius * 2)
            temp_overlay = self.overlay.copy()
            cv2.line(temp_overlay, (self.last_x, self.last_y), (x, y), (255, 0, 255), self.paint_radius * 2)

        # Combine the painted part with the existing overlay using 20% opacity
        painted_region = (self.paint_mask == 1)
        non_painted_region = self.overlay[:, :, 0] != 255  # Avoid repainting already painted areas
        final_mask = painted_region & non_painted_region
        
        # Update overlay only for unpainted areas
        self.overlay[final_mask] = cv2.addWeighted(temp_overlay, 0.2, self.overlay, 0.8, 0)[final_mask]

        # Update the canvas with the painted overlay
        self.update_canvas(self.overlay)
