import cv2
import numpy as np
import tkinter as tk
from tkinter import simpledialog

tested_urls = []

def search_html_stream(url):
    # Create a VideoCapture object
    cap = cv2.VideoCapture(url)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print("Unable to read camera feed")
        return False
    
    # Default resolutions of the frame are obtained
    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))
     
    # Define the codec and create VideoWriter object
    out = cv2.VideoWriter('outpy.avi', 
                         cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 
                         10, 
                         (frame_width, frame_height))
    
    frame_count = 0
    try:
        while frame_count < 250:
            ret, frame = cap.read()
            if not ret:
                break
                
            out.write(frame)
            cv2.imshow('frame', frame)
            frame_count += 1
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        return True
    finally:
        # Clean up resources
        cap.release()
        out.release()
        cv2.destroyAllWindows()

def test_camera(url):
    success = search_html_stream(url)
    return success

def creat_main_window():
    root = tk.Tk()
    root.title("Camera Stream Test")
    root.geometry("400x300")

    def on_test_button_click():
        def on_select(event):
            selected_url = url_var.get()
            url_entry.delete(0, tk.END)
            url_entry.insert(0, selected_url)

        dialog = tk.Toplevel(root)
        dialog.title("Input")
        dialog.geometry("300x200")

        tk.Label(dialog, text="Enter the camera URL:").pack(pady=5)
        
        url_var = tk.StringVar()
        url_entry = tk.Entry(dialog, textvariable=url_var, width=40)
        url_entry.pack(pady=5)

        if tested_urls:
            tk.Label(dialog, text="Previously tested URLs:").pack(pady=5)
            url_dropdown = tk.OptionMenu(dialog, url_var, *tested_urls, command=on_select)
            url_dropdown.pack(pady=5)

        def on_ok():
            dialog.destroy()
            url = url_var.get()
            if url:
                success = test_camera(url)
                if success:
                    result_label.config(text="Camera stream was successful. Output file: outpy.avi")
                    create_watch_window(url)
                    tested_urls.append(url)
                else:
                    result_label.config(text="Camera stream failed.")

        ok_button = tk.Button(dialog, text="OK", width=10, command=on_ok)
        ok_button.pack(pady=20)

        dialog.transient(root)
        dialog.grab_set()
        root.wait_window(dialog)
    
    def create_watch_window(url):
        watch_window = tk.Toplevel(root)
        watch_window.title("Watch Camera Stream")
        watch_window.geometry("400x300")

        def on_watch_button_click():
            cap = cv2.VideoCapture(url)
            if not cap.isOpened():
                watch_label.config(text="Unable to read camera feed")
                return

            def update_frame():
                ret, frame = cap.read()
                if ret:
                    cv2.imshow('Watch Stream', frame)
                    watch_window.after(10, update_frame)
                else:
                    cap.release()
                    cv2.destroyAllWindows()

            update_frame()

        watch_button = tk.Button(watch_window, text="Watch Stream", width=15, command=on_watch_button_click)
        watch_button.pack(pady=20)

        watch_label = tk.Label(watch_window, text="")
        watch_label.pack(pady=20)

    test_button = tk.Button(root, text="Test Camera", width=15, command=on_test_button_click)
    test_button.pack(pady=20)

    result_label = tk.Label(root, text="")
    result_label.pack(pady=20)

    root.mainloop()
    

def main():
    creat_main_window()

if __name__ == "__main__":
    main()

