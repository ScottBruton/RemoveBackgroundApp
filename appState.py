# appState.py
import cv2
import numpy as np

# List to store selected edges globally across the application
selected_edges = []
# Variable to store the overlay of selected edges
selected_edges_overlay = None  

# Initial default value for the gap-filling level
gap_filling_level = 3

def get_gap_filling_level():
    """
    Returns the current gap filling level.
    This function provides access to the global variable `gap_filling_level`.

    Returns:
    - int: The current gap filling level.
    """
    global gap_filling_level
    print(f"[DEBUG] get_gap_filling_level() called. Returning gap_filling_level: {gap_filling_level}")
    return gap_filling_level

def set_gap_filling_level(new_level):
    """
    Sets the gap filling level to a new integer value.

    Parameters:
    - new_level (int or float): The new gap filling level to set. Must be a scalar integer or float.

    Raises:
    - ValueError: If new_level is not a scalar integer or float.
    """
    global gap_filling_level
    print(f"[DEBUG] set_gap_filling_level({new_level}) called.")
    
    # Check if the new level is a scalar integer or float
    if isinstance(new_level, (int, float)):
        # Convert to integer if valid and set it as the new gap filling level
        gap_filling_level = int(new_level)
        print(f"[DEBUG] gap_filling_level set to {gap_filling_level}")
    else:
        # Raise an error if the input is not a scalar number
        raise ValueError("[ERROR] gap_filling_level must be a scalar integer or float.")

# Method to save the overlay to appState
def save_overlay(overlay):
    """
    Saves the provided overlay image to `selected_edges_overlay` for persistent storage.

    Parameters:
    - overlay (np.ndarray): The overlay image with selected edges to save.
    """
    global selected_edges_overlay
    # Save a copy of the overlay image
    selected_edges_overlay = overlay.copy()
    print(f"[DEBUG] Overlay saved to selected_edges_overlay.")

# Method to retrieve the overlay from appState
def get_overlay():
    """
    Retrieves the stored overlay from `selected_edges_overlay`.

    Returns:
    - np.ndarray or None: A copy of the overlay if it exists, otherwise None.
    """
    global selected_edges_overlay
    if selected_edges_overlay is not None:
        print(f"[DEBUG] Returning a copy of selected_edges_overlay.")
        return selected_edges_overlay.copy()
    else:
        print(f"[DEBUG] No overlay found. Returning None.")
        return None

def find_edges_in_region(image_region, gap_filling_level=None, existing_edge_mask=None):
    """
    Applies edge detection on the provided image region and returns the edge mask, contours, and the processed image.
    
    This function performs bilateral filtering, Gaussian blurring, Canny edge detection, and morphological dilation
    to fill gaps within the edges. If an existing edge mask is provided, it merges the new edges with the existing mask.

    Parameters:
    - image_region (np.ndarray): The region of the image to process.
    - gap_filling_level (int, optional): The intensity level for gap filling. If None, retrieves the global gap filling level.
    - existing_edge_mask (np.ndarray, optional): A binary mask of previously detected edges to merge with the new edges.

    Returns:
    - edge_mask (np.ndarray): The binary edge mask showing detected edges.
    - contours (list): A list of contours outlining detected edges.
    - merged_edges (np.ndarray): The resulting image region with merged edges.
    
    Raises:
    - ValueError: If gap_filling_level is not a scalar integer.
    """
    print("[DEBUG] find_edges_in_region called.")
    
    # If no specific gap filling level is provided, use the global gap filling level
    if gap_filling_level is None:
        gap_filling_level = get_gap_filling_level()
        print(f"[DEBUG] No gap_filling_level provided. Using global gap_filling_level: {gap_filling_level}")
    
    # Ensure gap_filling_level is a scalar integer
    if isinstance(gap_filling_level, (list, np.ndarray)):
        # Handle case where gap_filling_level is an array or list
        print(f"[DEBUG] gap_filling_level is a list/array: {gap_filling_level}")
        gap_filling_level = gap_filling_level[0] if len(gap_filling_level) == 1 else int(get_gap_filling_level())
    try:
        # Convert gap_filling_level to an integer if it's a scalar
        gap_filling_level = int(gap_filling_level)
        print(f"[DEBUG] gap_filling_level successfully converted to integer: {gap_filling_level}")
    except ValueError as e:
        print(f"[ERROR] gap_filling_level must be a scalar integer. Received: {gap_filling_level}")
        raise ValueError("gap_filling_level must be an integer") from e

    # Step 1: Apply bilateral filtering to reduce noise while preserving edges
    print("[DEBUG] Applying bilateral filter.")
    bilateral_filtered = cv2.bilateralFilter(image_region, 9, 75, 75)
    
    # Step 2: Apply Gaussian blur to further smooth the image
    print("[DEBUG] Applying Gaussian blur.")
    blurred = cv2.GaussianBlur(bilateral_filtered, (5, 5), 0)
    
    # Step 3: Perform Canny edge detection to identify edges in the image
    print("[DEBUG] Performing Canny edge detection.")
    edges = cv2.Canny(blurred, 30, 100)
    
    # Step 4: Use morphological dilation to fill small gaps in the edges
    print(f"[DEBUG] Applying morphological dilation with iterations: {gap_filling_level}")
    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    dilated_edges = cv2.dilate(edges, kernel, iterations=gap_filling_level)
    
    # Step 5: Find contours from the edge mask
    print("[DEBUG] Finding contours from dilated edges.")
    contours, _ = cv2.findContours(dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Step 6: Create a binary mask for detected edges
    print("[DEBUG] Creating binary mask for detected edges.")
    edge_mask = np.zeros_like(dilated_edges)
    cv2.drawContours(edge_mask, contours, -1, 255, thickness=cv2.FILLED)
    
    # Step 7: Merge with existing edges if provided
    if existing_edge_mask is not None:
        print("[DEBUG] Merging with existing edge mask.")
        # Ensure existing_edge_mask is of type uint8
        if existing_edge_mask.dtype != np.uint8:
            existing_edge_mask = (existing_edge_mask * 255).astype(np.uint8)
        merged_edges = cv2.bitwise_or(edge_mask, existing_edge_mask)
    else:
        merged_edges = edge_mask
        print("[DEBUG] No existing edge mask provided. Using generated edge mask.")

    # Return the edge mask, contours, and the merged edges for integration with previously found edges
    print("[DEBUG] Returning edge mask, contours, and merged edges.")
    return edge_mask, contours, merged_edges
