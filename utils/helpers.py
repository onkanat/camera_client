def get_videowriter_fourcc(*args):
    """Video writer için FOURCC codec"""
    import cv2
    return cv2.VideoWriter_fourcc(*args)

def get_widget_position(widget):
    """Widget pozisyonunu al"""
    x = widget.winfo_rootx()
    y = widget.winfo_rooty()
    return x, y