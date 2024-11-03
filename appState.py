# appState.py

selected_edges = []
selected_edges_overlay = None  # To store the current overlay with selected edges

# Method to save the overlay to appState
def save_overlay(overlay):
    global selected_edges_overlay
    selected_edges_overlay = overlay.copy()

# Method to retrieve the overlay from appState
def get_overlay():
    global selected_edges_overlay
    return selected_edges_overlay.copy() if selected_edges_overlay is not None else None
