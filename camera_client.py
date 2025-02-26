#! ./venv/bin/python
# -*- coding: utf-8 -*-
# Author: @Hakan KILIÇASLAN - 2025
# License: MIT

import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pytesseract
import threading
import logging
from datetime import datetime
import os
import time
import yaml
from tkinter import filedialog
import json
from collections import deque
from threading import Lock
from ui.shortcuts import ShortcutManager
from ui.help import HelpWindow
from ui.theme import ThemeManager

global tested_urls, ocr_text_buffer
global ocr_text_alarm_words
global save_ocr_text
global video_recorder
tested_urls = []
ocr_text_buffer = [] # max buffer size = 100
ocr_text_alarm_words = []
save_ocr_text = False
video_recorder = None

class Config:
    def __init__(self):
        self.config = {}
        self.config_file = "config.yaml"
        self.load_config()
    
    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f)
            logging.info(f"Configuration loaded from {self.config_file}")
        except FileNotFoundError:
            logging.warning(f"Configuration file {self.config_file} not found, using defaults")
            self.create_default_config()
    
    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logging.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logging.error(f"Failed to save configuration: {str(e)}")
    
    def create_default_config(self):
        self.config = {
            'camera': {
                'default_url': 'http://localhost:8080/video_feed',
                'frame_width': 640,
                'frame_height': 480,
                'connection_timeout': 10
            },
            'ocr': {
                'buffer_size': 100,
                'save_detected_text': False,
                'text_save_directory': 'detected_texts',
                'tesseract_path': '/usr/local/bin/tesseract',
                'preprocessing': {
                    'enabled': False,
                    'resize_width': 640,
                    'denoise': True,
                    'threshold_method': 'adaptive',
                    'contrast_enhance': True,
                    'deskew': True
                }
            },
            'alarm': {
                'default_words': ["599:", "home theater", "smoke", "danger", "alert", "warning", "hazard", "emergency"],
                'words_file': 'alarm_words.txt'
            },
            'logging': {
                'level': 'INFO',
                'directory': 'logs',
                'format': '%(asctime)s - %(levelname)s - %(message)s'
            },
            'recording': {
                'enabled': False,
                'output_directory': 'recordings',
                'format': 'XVID',
                'fps': 20,
                'resolution': {
                    'width': 640,
                    'height': 480
                },
                'pre_alarm_duration': 5,
                'post_alarm_duration': 10
            }
        }
        self.save_config()

# Global config instance
config = Config()

# Log yapılandırması
def setup_logging():
    log_dir = config.config['logging']['directory']
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"camera_client_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging system initialized")

def save_detected_text(text, detected_time=None):
    """OCR ile tespit edilen metni dosyaya kaydet"""
    if not text.strip():
        return
        
    save_dir = config.config['ocr']['text_save_directory']
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    filename = os.path.join(save_dir, f"ocr_text_{datetime.now().strftime('%Y%m%d')}.txt")
    timestamp = detected_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {text.strip()}\n")
    logging.info(f"Detected text saved to {filename}")

class OCRDetection:
    def __init__(self, text, timestamp=None):
        self.text = text.strip()
        self.timestamp = timestamp or datetime.now()
    
    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] {self.text}"

# OCR buffer'ı güncelleme
ocr_text_buffer = []  # Artık OCRDetection nesnelerini saklayacak

class ImagePreprocessor:
    @staticmethod
    def preprocess_image(image, config):
        if not config.config['ocr']['preprocessing']['enabled']:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Resize
        width = config.config['ocr']['preprocessing']['resize_width']
        height = int(width * image.shape[0] / image.shape[1])
        image = cv2.resize(image, (width, height))

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Denoise
        if config.config['ocr']['preprocessing']['denoise']:
            gray = cv2.fastNlMeansDenoising(gray)

        # Threshold
        method = config.config['ocr']['preprocessing']['threshold_method']
        if method == 'simple':
            _, gray = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        elif method == 'adaptive':
            gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
        elif method == 'otsu':
            _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Contrast enhancement
        if config.config['ocr']['preprocessing']['contrast_enhance']:
            gray = cv2.equalizeHist(gray)

        # Deskew
        if config.config['ocr']['preprocessing']['deskew']:
            gray = ImagePreprocessor.deskew(gray)

        return gray

    @staticmethod
    def deskew(image):
        coords = np.column_stack(np.where(image > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, 
                                borderMode=cv2.BORDER_REPLICATE)
        return rotated

class VideoRecorder:
    def __init__(self, config):
        self.config = config
        self.recording = False
        self.writer = None
        self.frame_buffer = deque(maxlen=int(config.config['recording']['pre_alarm_duration'] * 
                                           config.config['recording']['fps']))
        self.lock = Lock()
        self._setup_output_dir()
        logging.info("VideoRecorder initialized")
    
    def _setup_output_dir(self):
        out_dir = self.config.config['recording']['output_directory']
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
    
    def add_frame(self, frame):
        if frame is not None:
            self.frame_buffer.append(frame)
            if self.recording and self.writer:
                with self.lock:
                    self.writer.write(frame)
    
    def start_recording(self):
        if self.recording:
            logging.info("Recording already in progress")
            return
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(
                self.config.config['recording']['output_directory'],
                f'alarm_recording_{timestamp}.avi'
            )
            
            fourcc = cv2.VideoWriter_fourcc(*'XVID')  # type: ignore # XVID codec kullan
            self.writer = cv2.VideoWriter(
                filename,
                fourcc,
                self.config.config['recording']['fps'],
                (self.config.config['recording']['resolution']['width'],
                 self.config.config['recording']['resolution']['height'])
            )
            
            if not self.writer.isOpened():
                raise Exception("Failed to create video writer")
            
            # Write pre-alarm buffer
            with self.lock:
                for frame in self.frame_buffer:
                    self.writer.write(frame)
            
            self.recording = True
            logging.info(f"Started recording to {filename}")
            
        except Exception as e:
            self.recording = False
            if self.writer:
                self.writer.release()
                self.writer = None
            logging.error(f"Error starting recording: {str(e)}")
            raise
    
    def stop_recording(self):
        if not self.recording:
            return
        
        self.recording = False
        with self.lock:
            if self.writer:
                self.writer.release()
                self.writer = None
        logging.info("Stopped recording")

def create_main_window():
    global video_recorder  # Global değişkeni fonksiyon içinde kullanabilmek için
    
    root = tk.Tk()
    root.title("Camera Stream Monitor")
    root.geometry("1024x768")

    # Shortcuts manager'ı başlat
    shortcuts = ShortcutManager(root)
    
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, pady=1)

    test_frame = tk.Frame(main_frame)
    test_frame.pack(fill=tk.BOTH, expand=True)

    url_frame = tk.Frame(test_frame)
    url_frame.pack(pady=1)
    
    tk.Label(url_frame, text="Kamera URL:").pack(side=tk.LEFT)
    url_entry = tk.Entry(url_frame, width=40)
    url_entry.pack(side=tk.LEFT, padx=1)
    
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

    def handle_alarm(word):
        """Alarm tetiklendiğinde yapılacak işlemler"""
        global video_recorder
        
        logging.info(f"Alarm triggered for word: {word}")
        status_label.config(text=f"ALARM! Tehlikeli kelime bulundu: {word}")
        
        if not video_recorder:
            logging.error("Video recorder not initialized")
            return

        try:
            if config.config['recording']['enabled']:
                if not video_recorder.recording:
                    video_recorder.start_recording()
                    recording_status.config(text="Recording...", fg="red")
                    
                    # Post-alarm kaydını durdurmak için zamanlayıcı
                    root.after(
                        config.config['recording']['post_alarm_duration'] * 1000,
                        lambda: stop_recording(word)
                    )
        except Exception as e:
            logging.error(f"Error in alarm handling: {str(e)}")
            messagebox.showerror("Hata", f"Video kaydı başlatılamadı: {str(e)}")

    def stop_recording(word):
        """Kayıt durdurma işlemi"""
        try:
            if video_recorder and video_recorder.recording:
                video_recorder.stop_recording()
                recording_status.config(text="Not Recording", fg="gray")
                logging.info(f"Stopped recording for alarm word: {word}")
        except Exception as e:
            logging.error(f"Error stopping recording: {str(e)}")

    def continuous_alarm_check():
        """Sürekli alarm kontrolü yapan thread"""
        while True:
            try:
                detected_word = ocr_text_alarm_detection(ocr_text_alarm_words, ocr_text_buffer)
                if detected_word:
                    # GUI güncellemelerini ana thread'de yap
                    root.after(0, lambda w=detected_word: handle_alarm(w))
            except Exception as e:
                logging.error(f"Error in alarm check: {str(e)}")
            finally:
                time.sleep(1.0)  # Her saniye kontrol et

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

    def toggle_save_text():
        global save_ocr_text
        save_ocr_text = not save_ocr_text
        if save_ocr_text:
            save_button.config(text="Stop Saving")
            logging.info("Text saving enabled")
        else:
            save_button.config(text="Start Saving")
            logging.info("Text saving disabled")

    # Add save button after other buttons
    save_button = tk.Button(button_frame, text="Start Saving", command=toggle_save_text)
    save_button.pack(side=tk.LEFT, padx=5)

    button_frame_alarm = tk.Frame(test_frame)
    button_frame_alarm.pack(side=tk.RIGHT, pady=5)
    
    tk.Button(button_frame_alarm, text="Clear Alarm", command=clear_alarm_status).pack(side=tk.RIGHT, pady=2)
    tk.Button(button_frame_alarm, text="Reset Alarm", command=reset_alarm_detection).pack(side=tk.RIGHT, pady=2)
    

    alarm_words_frame = tk.Frame(test_frame)
    alarm_words_frame.pack(pady=5)
    
    tk.Label(alarm_words_frame, text="Alarm Words:").pack(side=tk.LEFT)
    alarm_words_entry = tk.Entry(alarm_words_frame, width=20)
    alarm_words_entry.pack(side=tk.LEFT, padx=5)
    
    def set_alarm_words():
        words = alarm_words_entry.get().strip()
        if words:
            global ocr_text_alarm_words
            ocr_text_alarm_words = words.split(',')
            messagebox.showinfo("Bilgi", "Alarm kelimeleri ayarlandı.")
            
    def handle_export():
        if export_alarm_words():
            messagebox.showinfo("Başarılı", "Alarm kelimeleri dışa aktarıldı.")
            
    def handle_import():
        if import_alarm_words():
            alarm_words_entry.delete(0, tk.END)
            alarm_words_entry.insert(0, ",".join(ocr_text_alarm_words))
            messagebox.showinfo("Başarılı", "Alarm kelimeleri içe aktarıldı.")

    tk.Button(alarm_words_frame, text="Set Alarm Words", command=set_alarm_words).pack(side=tk.LEFT)
    tk.Button(alarm_words_frame, text="Export Words", command=handle_export).pack(side=tk.LEFT, padx=5)
    tk.Button(alarm_words_frame, text="Import Words", command=handle_import).pack(side=tk.LEFT)

    status_frame = tk.Frame(main_frame)
    status_frame.pack(fill=tk.X, pady=10)
    status_label = tk.Label(status_frame, text="Hazır", bd=1, relief=tk.SUNKEN, anchor=tk.W)
    status_label.pack(fill=tk.X)

    def load_settings():
        config.load_config()
        # Update GUI elements with new config
        url_entry.delete(0, tk.END)
        url_entry.insert(0, config.config['camera']['default_url'])
        canvas.config(width=config.config['camera']['frame_width'],
                     height=config.config['camera']['frame_height'])
        messagebox.showinfo("Bilgi", "Ayarlar yüklendi")

    def save_settings():
        # Update config from GUI elements
        config.config['camera']['default_url'] = url_entry.get()
        config.save_config()
        messagebox.showinfo("Bilgi", "Ayarlar kaydedildi")

    # Add settings buttons to button_frame
    settings_frame = tk.Frame(test_frame)
    settings_frame.pack(pady=5)
    tk.Button(settings_frame, text="Load Settings", command=load_settings).pack(side=tk.LEFT, padx=5)
    tk.Button(settings_frame, text="Save Settings", command=save_settings).pack(side=tk.LEFT, padx=5)

    # Initialize with config values
    url_entry.insert(0, config.config['camera']['default_url'])

    # OCR sonuçları için yeni bir frame ekle
    ocr_results_frame = tk.Frame(main_frame)
    ocr_results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    
    ocr_text = tk.Text(ocr_results_frame, height=5, width=70)
    ocr_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(ocr_results_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    ocr_text.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=ocr_text.yview)
    
    def update_ocr_display():
        ocr_text.delete(1.0, tk.END)
        for detection in ocr_text_buffer[-10:]:  # Son 10 tespiti göster
            ocr_text.insert(tk.END, str(detection) + "\n")
        root.after(1000, update_ocr_display)  # Her saniye güncelle
    
    update_ocr_display()

    # Preprocessing control frame
    preproc_frame = tk.LabelFrame(test_frame, text="Image Preprocessing")
    preproc_frame.pack(pady=5, padx=5, fill=tk.X)

    def toggle_preprocessing():
        config.config['ocr']['preprocessing']['enabled'] = preproc_var.get()
        config.save_config()

    preproc_var = tk.BooleanVar(value=config.config['ocr']['preprocessing']['enabled'])
    tk.Checkbutton(preproc_frame, text="Enable Preprocessing", 
                   variable=preproc_var, command=toggle_preprocessing).pack(side=tk.LEFT)

    threshold_var = tk.StringVar(value=config.config['ocr']['preprocessing']['threshold_method'])
    tk.Label(preproc_frame, text="Threshold:").pack(side=tk.LEFT, padx=5)
    threshold_menu = tk.OptionMenu(preproc_frame, threshold_var, 
                                 "simple", "adaptive", "otsu",
                                 command=lambda x: config.save_config())
    threshold_menu.pack(side=tk.LEFT)

    # Video kaydı için global değişken
    video_recorder = VideoRecorder(config)

    # Video kayıt kontrolü için frame
    recording_frame = tk.LabelFrame(test_frame, text="Video Recording")
    recording_frame.pack(pady=5, padx=5, fill=tk.X)
    
    def toggle_recording_enabled():
        """Video kaydı aktif/pasif durumunu değiştir"""
        config.config['recording']['enabled'] = recording_var.get()
        config.save_config()
        logging.info(f"Recording enabled: {recording_var.get()}")
        
        # Eğer kayıt devre dışı bırakılıyorsa ve aktif kayıt varsa durdur
        if not recording_var.get() and video_recorder and video_recorder.recording:
            video_recorder.stop_recording()
    
    recording_var = tk.BooleanVar(value=config.config['recording']['enabled'])
    tk.Checkbutton(recording_frame, text="Enable Alarm Recording",
                   variable=recording_var, 
                   command=toggle_recording_enabled).pack(side=tk.LEFT)

    # Kayıt durumunu gösteren label
    recording_status = tk.Label(recording_frame, text="Not Recording", fg="gray")
    recording_status.pack(side=tk.LEFT, padx=5)

    # Alarm checking thread'ini başlat
    alarm_thread = threading.Thread(target=continuous_alarm_check, daemon=True)
    alarm_thread.start()

    # Kısayol tuşlarını kaydet
    shortcuts.register_shortcut("Control-t", lambda: test_camera_callback())
    shortcuts.register_shortcut("Control-o", lambda: start_ocr_callback())
    shortcuts.register_shortcut("Control-s", lambda: stop_all_processing())
    shortcuts.register_shortcut("Control-r", lambda: toggle_recording())
    shortcuts.register_shortcut("Control-l", lambda: toggle_theme())
    
    # Help menüsü ekle
    menu_bar = tk.Menu(root)
    root.config(menu=menu_bar)
    
    help_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Yardım", menu=help_menu)
    help_menu.add_command(label="Klavye Kısayolları (Ctrl+H)", 
                         command=lambda: HelpWindow(root))
    
    def toggle_theme():
        """Tema değiştirme fonksiyonu"""
        current_theme = ThemeManager().current_theme
        new_theme = "dark" if current_theme == "light" else "light"
        ThemeManager().apply_theme(root, new_theme)
    
    def stop_all_processing():
        """Tüm işlemleri durdur"""
        if video_recorder and video_recorder.recording:
            video_recorder.stop_recording()
        # Diğer işlemleri durdur...
        status_label.config(text="Tüm işlemler durduruldu")
    
    def toggle_recording():
        """Kayıt durumunu değiştir"""
        if video_recorder:
            if video_recorder.recording:
                video_recorder.stop_recording()
                recording_status.config(text="Not Recording", fg="gray")
            else:
                video_recorder.start_recording()
                recording_status.config(text="Recording...", fg="red")
    
    # Button frame'e Help butonu ekle
    tk.Button(button_frame, text="Yardım", 
             command=lambda: HelpWindow(root)).pack(side=tk.LEFT, padx=5)
    
    # Status bar'a kısayol bilgisi ekle
    status_label.config(text="Hazır (Ctrl+H için Yardım)")

    root.mainloop()

# Test for camera  stream from URL://localhost:8080/video_feed
class CameraConnectionError(Exception):
    """Camera bağlantı hatalarını yönetmek için özel exception sınıfı"""
    pass

def search_html_stream(url, canvas, root):
    try:
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            raise CameraConnectionError("Kamera akışı başlatılamadı")
        
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
    except CameraConnectionError as e:
        print(f"Kamera bağlantı hatası: {str(e)}")
        return False
    except Exception as e:
        print(f"Beklenmeyen hata: {str(e)}")
        return False
    finally:
        if 'cap' in locals():
            cap.release() # type: ignore

# Watch the camera stream from URL://localhost:8080/video_feed
def html_stream(url, canvas, root):
    cap = None
    try:
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            raise CameraConnectionError("Kamera akışı başlatılamadı")
        
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
                    
    except CameraConnectionError as e:
        messagebox.showerror("Bağlantı Hatası", str(e))
    except Exception as e:
        messagebox.showerror("Beklenmeyen Hata", f"Bir hata oluştu: {str(e)}")
    finally:
        if cap is not None:
            cap.release()

# Test for camera stream from URL://localhost:8080/video_feed
def test_camera(url, canvas, root):
    try:
        if not url.startswith(('http://', 'https://', 'rtsp://')):
            logging.error(f"Invalid camera URL format: {url}")
            raise CameraConnectionError("Geçersiz kamera URL formatı")
        
        logging.info(f"Testing camera connection for URL: {url}")
        success = search_html_stream(url, canvas, root)
        
        if not success:
            logging.error(f"Camera connection failed for URL: {url}")
            raise CameraConnectionError("Kamera bağlantısı başarısız")
        
        logging.info(f"Camera connection successful for URL: {url}")
        return success
        
    except Exception as e:
        logging.error(f"Error in test_camera: {str(e)}")
        messagebox.showerror("Hata", str(e))
        return False

# OCR text detection from camera stream from URL://localhost:8080/video_feed
def ocr_text_detection(url, canvas, root):
    global video_recorder  # Global değişkeni fonksiyon içinde kullanabilmek için
    
    logging.info(f"Starting OCR detection for URL: {url}")
    try:
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            logging.error("Failed to open camera feed")
            return
        
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            
            # Add frame to video buffer if recording is enabled
            if config.config['recording']['enabled'] and video_recorder:
                video_recorder.add_frame(frame.copy())
            
            # Preprocess the frame
            processed_frame = ImagePreprocessor.preprocess_image(frame, config)
            
            # Use pytesseract to do OCR on the processed frame
            text = pytesseract.image_to_string(processed_frame)
            
            if text.strip():
                detection = OCRDetection(text)
                ocr_text_buffer.append(detection)
                if len(ocr_text_buffer) > config.config['ocr']['buffer_size']:
                    ocr_text_buffer.pop(0)
                
                if save_ocr_text:
                    save_detected_text(text, detection.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
                logging.info(f"OCR detected: {str(detection)}")
            
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
                
    except Exception as e:
        logging.error(f"Error in OCR detection: {str(e)}")
    finally:
        cap.release() # type: ignore
        logging.info("OCR detection stopped")

# OCR text alarm detection ocr_text_alarm_words = ["599:","home theater", "smoke", "danger", "alert", "warning", "hazard", "emergency"]
# Check if any of the alarm words are present in the text buffer
def ocr_text_alarm_detection(ocr_text_alarm_words, ocr_text_buffer):
    """Return tetiklenen alarm kelimesini veya None"""
    try:
        if not ocr_text_alarm_words or not ocr_text_buffer:
            return None

        if isinstance(ocr_text_alarm_words, str):
            ocr_text_alarm_words = [word.strip() for word in ocr_text_alarm_words.split(',')]
        
        for word in ocr_text_alarm_words:
            if not word:
                continue
                
            for detection in ocr_text_buffer:
                if word.lower() in detection.text.lower():
                    logging.warning(f"ALARM! Dangerous word detected: {word} at {detection.timestamp}")
                    return word
    except Exception as e:
        logging.error(f"Error in alarm detection: {str(e)}")
    
    return None

# Load the alarm words from a file and add to ocr_text_alarm_words
def load_alarm_words(filename=None):
    global ocr_text_alarm_words
    filename = filename or config.config['alarm']['words_file']
    try:
        with open(filename, 'r') as f:
            ocr_text_alarm_words = [word.strip() for word in f.readlines() if word.strip()]
    except FileNotFoundError:
        # Default list if file not found
        ocr_text_alarm_words = ["599:", "home theater", "smoke", "danger", "alert", "warning", "hazard", "emergency"]

def export_alarm_words(filename=None):
    """Alarm kelimelerini JSON formatında dışa aktar"""
    if filename is None:
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Alarm Kelimelerini Kaydet"
        )
    
    if filename:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'alarm_words': ocr_text_alarm_words,
                    'exported_at': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            logging.info(f"Alarm words exported to {filename}")
            return True
        except Exception as e:
            logging.error(f"Failed to export alarm words: {str(e)}")
            messagebox.showerror("Hata", f"Dışa aktarma başarısız: {str(e)}")
            return False

def import_alarm_words(filename=None):
    """JSON formatındaki alarm kelimelerini içe aktar"""
    if filename is None:
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Alarm Kelimelerini Yükle"
        )
    
    if filename:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                global ocr_text_alarm_words
                ocr_text_alarm_words = data['alarm_words']
            logging.info(f"Alarm words imported from {filename}")
            return True
        except Exception as e:
            logging.error(f"Failed to import alarm words: {str(e)}")
            messagebox.showerror("Hata", f"İçe aktarma başarısız: {str(e)}")
            return False
 

if __name__ == "__main__":
    setup_logging()
    load_alarm_words()
    logging.info("Application starting...")
    create_main_window()
    logging.info("Application shutting down...")
