from typing import Optional, Tuple
import cv2

def get_videowriter_fourcc(*args: str) -> int:
    """Safe wrapper for cv2.VideoWriter_fourcc"""
    return cv2.VideoWriter_fourcc(*args)

def get_widget_position(widget) -> Tuple[int, int]:
    """Get widget position for tooltip"""
    try:
        x = widget.winfo_rootx() + widget.winfo_width()
        y = widget.winfo_rooty() + widget.winfo_height()//2
        return x, y
    except:
        return 0, 0
