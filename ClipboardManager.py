import cv2
import numpy as np
import win32clipboard
from PIL import Image as PilImage
from io import BytesIO

def copy_objects_to_clipboard(open_cv_image, selected_objects):
    copied_image = np.zeros((open_cv_image.shape[0], open_cv_image.shape[1], 4), dtype=np.uint8)
    for contour in selected_objects:
        mask = np.zeros_like(open_cv_image[:, :, 0], dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)
        for c in range(3):
            copied_image[:, :, c] = cv2.bitwise_and(open_cv_image[:, :, c], open_cv_image[:, :, c], mask=mask)
        copied_image[:, :, 3] = mask
    output = PilImage.fromarray(copied_image, 'RGBA')
    output_buffer = BytesIO()
    output.save(output_buffer, format='BMP')
    data = output_buffer.getvalue()[14:]
    output_buffer.close()

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()
