#! ./venv/bin/python
# -*- coding: utf-8 -*-
# Author: @Hakan KILIÇASLAN - 2025
# License: MIT

import cv2
import numpy as np
import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk
import pytesseract
import threading

global tested_urls, ocr_text_buffer
global ocr_text_alarm_words
tested_urls = []
ocr_text_buffer = [] # max buffer size = 100
ocr_text_alarm_words = []

# TODO: Add a button for setting alarm words
# TODO: Add a status label for showing the alarm status

def create_main_window():
    root = tk.Tk()
    root.title("Camera Stream Test")
    root.geometry("800x600")

    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, pady=10)

    test_frame = tk.Frame(main_frame)
    test_frame.pack(fill=tk.BOTH, expand=True)

    url_frame = tk.Frame(test_frame)
    url_frame.pack(pady=10)
    
    tk.Label(url_frame, text="Kamera URL:").pack(side=tk.LEFT)
    url_entry = tk.Entry(url_frame, width=40)
    url_entry.pack(side=tk.LEFT, padx=5)
    
    canvas = tk.Canvas(main_frame, width=640, height=480)
    canvas.pack()

    def test_camera_callback():
        url = url_entry.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen bir URL girin!")
            return
        
        if url in tested_urls:
            messagebox.showinfo("Bilgi", "Bu URL zaten test edildi!")
            return
        
        handle_test_camera(url)
    
    def handle_test_camera(url):
        success = test_camera(url, canvas, root)
        if success:
            tested_urls.append(url)
            messagebox.showinfo("Başarılı", "Kamera bağlantısı başarılı!")
        else:
            messagebox.showerror("Hata", "Kamera bağlantısı başarısız!")
    
    def watch_stream_callback():
        url = url_entry.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen bir URL girin!")
            return
        html_stream(url, canvas, root)

    def start_ocr_callback():
        url = url_entry.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen bir URL girin!")
            return
        
        if url not in tested_urls:
            if not messagebox.askyesno("Uyarı", "Bu URL henüz test edilmedi. Devam etmek istiyor musunuz?"):
                return
        
        # Run OCR directly
        ocr_text_detection(url, canvas, root)

    def continuous_alarm_check():
        while True:
            if ocr_text_alarm_detection(ocr_text_alarm_words, ocr_text_buffer):
                root.after(0, lambda: status_label.config(text="ALARM! Tehlikeli kelime bulundu!"))
            threading.Event().wait(1.0)  # Check every second

    def clear_alarm_status():
        status_label.config(text="Hazır")
    
    def reset_alarm_detection():
        global ocr_text_buffer
        ocr_text_buffer.clear()
        status_label.config(text="Alarm durumu sıfırlandı.")

    button_frame = tk.Frame(test_frame)
    button_frame.pack(pady=5)
    
    tk.Button(button_frame, text="Test Et", command=test_camera_callback).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="OCR Başlat", command=start_ocr_callback).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Watch Stream", command=watch_stream_callback).pack(side=tk.LEFT, padx=5)

    button_frame_alarm = tk.Frame(test_frame)
    button_frame_alarm.pack(pady=5)
    
    tk.Button(button_frame_alarm, text="Clear Alarm", command=clear_alarm_status).pack(pady=2)
    tk.Button(button_frame_alarm, text="Reset Alarm", command=reset_alarm_detection).pack(pady=2)
    
    status_frame = tk.Frame(main_frame)
    status_frame.pack(fill=tk.X, pady=10)
    status_label = tk.Label(status_frame, text="Hazır", bd=1, relief=tk.SUNKEN, anchor=tk.W)
    status_label.pack(fill=tk.X)

    root.mainloop()

# Test for camera  stream from URL://localhost:8080/video_feed
def search_html_stream(url, canvas, root):
    # Create a VideoCapture object
    cap = cv2.VideoCapture(url)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print("Unable to read camera feed")
        return False
    
    frame_count = 0
    try:
        while frame_count < 25:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Convert the frame to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert the frame to a PIL image
            img = Image.fromarray(frame)
            # Convert the PIL image to an ImageTk image
            imgtk = ImageTk.PhotoImage(image=img)
            # Update the canvas with the new image
            canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
            root.update_idletasks()
            root.update()
            frame_count += 1
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        return True
    finally:
        # Clean up resources
        cap.release()

# Watch the camera stream from URL://localhost:8080/video_feed
def html_stream(url, canvas, root):
    # Create a VideoCapture object
    cap = cv2.VideoCapture(url)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print("Unable to read camera feed")
        return
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Convert the frame to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert the frame to a PIL image
            img = Image.fromarray(frame)
            # Convert the PIL image to an ImageTk image
            imgtk = ImageTk.PhotoImage(image=img)
            # Update the canvas with the new image
            canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
            root.update_idletasks()
            root.update()
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        # Clean up resources
        cap.release()

# Test for camera stream from URL://localhost:8080/video_feed
def test_camera(url, canvas, root):
    success = search_html_stream(url, canvas, root)
    return success

# OCR text detection from camera stream from URL://localhost:8080/video_feed
def ocr_text_detection(url, canvas, root):
    # Create a VideoCapture object
    cap = cv2.VideoCapture(url)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print("Unable to read camera feed")
        return
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            
            # Convert the frame to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Use pytesseract to do OCR on the frame
            text = pytesseract.image_to_string(gray)
            print(f"OCR Text: {text}")
            # Append the text to the buffer
            ocr_text_buffer.append(text)
            if len(ocr_text_buffer) > 100:  # maintain the buffer size
                ocr_text_buffer.pop(0)

            # Convert the frame to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert the frame to a PIL image
            img = Image.fromarray(frame)
            # Convert the PIL image to an ImageTk image
            imgtk = ImageTk.PhotoImage(image=img)
            # Update the canvas with the new image
            canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
            root.update_idletasks()
            root.update()
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        # Clean up resources
        cap.release()

# OCR text alarm detection ocr_text_alarm_words = ["599:","home theater", "smoke", "danger", "alert", "warning", "hazard", "emergency"]
# Check if any of the alarm words are present in the text buffer
def ocr_text_alarm_detection(ocr_text_alarm_words, ocr_text_buffer):
    # Convert comma-separated string to list if needed
    if isinstance(ocr_text_alarm_words, str):
        ocr_text_alarm_words = [word.strip() for word in ocr_text_alarm_words.split(',')]
    
    for word in ocr_text_alarm_words:
        for text in ocr_text_buffer:
            if word.lower() in text.lower():
                print(f"ALARM! Tehlikeli kelime bulundu: {word}")
                return True
    return False

# Load the alarm words from a file and add to ocr_text_alarm_words
def load_alarm_words(filename="alarm_words.txt"):
    global ocr_text_alarm_words
    try:
        with open(filename, 'r') as f:
            ocr_text_alarm_words = [word.strip() for word in f.readlines() if word.strip()]
    except FileNotFoundError:
        # Default list if file not found
        ocr_text_alarm_words = ["599:", "home theater", "smoke", "danger", "alert", "warning", "hazard", "emergency"]


if __name__ == "__main__":
    load_alarm_words()
    create_main_window()

