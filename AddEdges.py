import cv2
import appState
import numpy as np

class AddEdges:
    def __init__(self, root, canvas, open_cv_image, update_canvas, history, selected_edges, find_edges_button):
        self.root = root
        self.canvas = canvas
        self.open_cv_image = open_cv_image
        self.update_canvas = update_canvas
        self.history = history
        self.selected_edges = selected_edges
        self.find_edges_button = find_edges_button
        self.paint_radius = 10
        self.overlay = None
        self.paint_mask = np.zeros((open_cv_image.shape[0], open_cv_image.shape[1]), dtype=np.uint8)
        self.painted_areas = np.zeros((open_cv_image.shape[0], open_cv_image.shape[1]), dtype=np.uint8)
        self.last_x = None
        self.last_y = None
        self.is_painting = False
        self.has_painted = False

        # Bind the find edges button to the find_edges method
        self.find_edges_button.config(command=self.find_edges)
    def select_add_edges_tool(self):
        self.canvas.bind("<ButtonPress-1>", self.on_paint_start)
        self.canvas.bind("<B1-Motion>", self.on_paint)
        self.canvas.bind("<ButtonRelease-1>", self.on_paint_end)

        self.overlay = appState.get_overlay()
        if self.overlay is None:
            self.overlay = self.open_cv_image.copy()

        self.find_edges_button.config(state='disabled')

    def on_paint_start(self, event):
        self.is_painting = True
        self.last_x, self.last_y = event.x, event.y
        self.paint_path(event.x, event.y)

    def on_paint(self, event):
        if self.is_painting:
            self.paint_path(event.x, event.y)
            self.last_x, self.last_y = event.x, event.y

    def on_paint_end(self, event):
        self.is_painting = False
        appState.save_overlay(self.overlay)
        self.history.append(self.overlay.copy())
        self.last_x, self.last_y = None, None

        if self.has_painted:
            self.find_edges_button.config(state='normal')

    def paint_path(self, x, y):
        temp_overlay = self.overlay.copy()

        if not self.is_painting or (self.last_x is None or self.last_y is None):
            cv2.circle(self.paint_mask, (x, y), self.paint_radius, 1, -1)
            cv2.circle(temp_overlay, (x, y), self.paint_radius, (255, 0, 255), -1)
            self.is_painting = True
        else:
            cv2.line(self.paint_mask, (self.last_x, self.last_y), (x, y), 1, self.paint_radius * 2)
            cv2.line(temp_overlay, (self.last_x, self.last_y), (x, y), (255, 0, 255), self.paint_radius * 2)

        newly_painted_region = (self.paint_mask == 1) & (self.painted_areas == 0)

        if np.any(newly_painted_region):
            self.overlay[newly_painted_region] = cv2.addWeighted(
                temp_overlay[newly_painted_region], 0.6,
                self.overlay[newly_painted_region], 0.8, 0
            )
            self.painted_areas[newly_painted_region] = 1
            self.has_painted = True

        self.update_canvas(self.overlay)
        self.paint_mask.fill(0)

    def find_edges(self):
        # Define a gap_filling_level, for example, 3
        gap_filling_level = 3
    
        # Create a mask for the painted areas
        painted_mask = self.painted_areas > 0
    
        # Extract the region of interest (ROI) from the original image where painting was done
        roi = self.open_cv_image.copy()
        roi[~painted_mask] = 0  # Keep only the areas under the painted regions
    
        # Clear the painted areas from the overlay
        self.overlay[painted_mask] = self.open_cv_image[painted_mask]
    
        # Use the find_edges_in_region method from appState on the ROI
        edges, contours, merged_edges = appState.find_edges_in_region(
            roi,  # Pass the ROI
            gap_filling_level,  # Pass the gap filling level
            painted_mask.astype(np.uint8)  # Ensure the existing edge mask is uint8
        )
    
        # Ensure `edges` is single-channel before applying the mask
        if edges.ndim == 3:
            edges = cv2.cvtColor(edges, cv2.COLOR_BGR2GRAY)
    
        # Create a mask for the detected edges
        edge_mask = edges > 0
    
        # Apply the color overlay where edges are detected
        self.overlay[edge_mask] = (0, 255, 0)  # Color edges green
    
        # Update the canvas with the new overlay
        self.update_canvas(self.overlay)
    
        # Save the updated overlay to appState
        appState.save_overlay(self.overlay)
    
        # Reset the painted areas and paint mask for new painting
        self.painted_areas.fill(0)
        self.paint_mask.fill(0)
        self.has_painted = False
    
        # Disable the find edges button until new painting is done
        self.find_edges_button.config(state='disabled')