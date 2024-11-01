import ctypes
import os
from pystray import Icon as TrayIcon, MenuItem as item
from PIL import Image as PilImage
import pystray  # Ensure pystray is fully imported

def set_dpi_awareness():
    ctypes.windll.shcore.SetProcessDpiAwareness(2)

set_dpi_awareness()

def on_exit(icon, item):
    icon.stop()
    os._exit(0)

def setup_tray():
    icon_image = PilImage.open("icon.ico")  # Ensure icon.ico is in your directory
    icon = pystray.Icon("NoBackgroundSnipper", icon_image, menu=pystray.Menu(item('Exit', on_exit)))
    icon.run()
