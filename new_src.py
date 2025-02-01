import mss
import numpy as np
import cv2

import mss
from PIL import Image
from io import BytesIO

def screen_grab(monitor=1, as_bytes=False):
    """
    Captures a screenshot of the specified monitor and returns it as a PIL image or byte stream.
    
    Args:
        monitor (int): The monitor index to capture (default is 1 for the first monitor).
        as_bytes (bool): If True, returns the screenshot as a BytesIO object instead of a PIL image.
        
    Returns:
        Image.Image or BytesIO: The captured screenshot as a PIL Image object or in-memory byte stream.
    """
    try:
        with mss.mss() as sct:
            # Validate monitor index
            monitors = sct.monitors
            if monitor < 1 or monitor >= len(monitors):
                raise ValueError(f"Invalid monitor index. Available monitors: {len(monitors) - 1}")
            
            # Capture the specified monitor
            screenshot = sct.grab(monitors[monitor])
            
            # Convert the screenshot to a PIL image
            image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            
            if as_bytes:
                # Convert image to a BytesIO stream if requested
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                buffer.seek(0)
                return buffer
            
            return image
    except Exception as e:
        raise RuntimeError(f"Error capturing screen: {e}")

# Example Usage:
# img = screen_grab(monitor=1)  # Returns a PIL image of the first monitor
# img_bytes = screen_grab(monitor=1, as_bytes=True)  # Returns a BytesIO stream


def capture_screen():
    """MSS"""
    pass

def locate_chess_board():
    """YOLO"""
    pass

def board_to_fen():
    """SPLIT BOARD + MOST SIMILAR"""
    pass

def get_turn():
    pass