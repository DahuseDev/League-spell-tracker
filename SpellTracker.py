# pip install PySide6 requests pygetwindow google-cloud-firestore firebase-admin tqdm
import sys
from PySide6.QtWidgets import QApplication
from src.widgets.OverlayWidget import OverlayWidget
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import threading


def create_image():
    # Generate an image and draw a pattern
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), "black")
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        (width // 2, 0, width, height // 2),
        fill="white")
    dc.rectangle(
        (0, height // 2, width // 2, height),
        fill="white")

    return image

def on_quit(icon, item):
    icon.stop()
    QApplication.quit()

def run_tray_icon():
    # Create the tray icon
    icon = Icon("Spell Tracker")
    icon.icon = create_image()
    icon.title = "League Spell Tracker"
    icon.menu = Menu(
        MenuItem("Quit", on_quit)
    )
    icon.run()

# ================================ MAIN ========================================
if __name__ == "__main__":
    # Start the tray icon in a separate thread
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()

    # Start the Qt application
    app = QApplication(sys.argv)
    w = OverlayWidget()
    sys.exit(app.exec())
