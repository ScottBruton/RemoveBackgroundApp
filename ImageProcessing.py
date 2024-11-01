import cv2
import numpy as np
from appState import selected_objects, contours, edge_mask

def process_image(image):
    open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGR)
    return open_cv_image

def extract_objects(open_cv_image):
    global edge_mask, contours
    bilateral_filtered = cv2.bilateralFilter(open_cv_image, 9, 75, 75)
    blurred = cv2.GaussianBlur(bilateral_filtered, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 100)
    edge_mask = edges

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return edge_mask, contours

def handle_contour_coloring(image, selected_contours, all_contours):
    overlay = image.copy()
    for contour in selected_contours:
        if contour is not None and len(contour) > 0:
            color = (173, 216, 230)
            cv2.drawContours(overlay, [contour], -1, color, 2)
    for contour in all_contours:
        if contour is not None and len(contour) > 0 and not any(np.array_equal(contour, selected) for selected in selected_contours):
            color = (0, 255, 0)
            cv2.drawContours(overlay, [contour], -1, color, 2)
    return overlay
