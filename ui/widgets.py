import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict, Any
from .styles import StyleManager
import time
from utils.helpers import get_widget_position

class LabeledEntry(ttk.Frame):
    def __init__(self, master, label_text: str, width: int = 20, **kwargs):
        super().__init__(master, style=StyleManager.get_widget_style('frame'))
        
        self.label = ttk.Label(self, text=label_text, 
                              style=StyleManager.get_widget_style('label'))
        self.label.pack(side=tk.LEFT, padx=StyleManager.PADDING['small'])
        
        self.entry = ttk.Entry(self, width=width,
                              style=StyleManager.get_widget_style('entry'))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                       padx=StyleManager.PADDING['small'])

class StatusBar(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, style=StyleManager.get_widget_style('frame'))
        
        self.status_label = ttk.Label(self, text="Ready",
                                     style=StyleManager.get_widget_style('label'))
        self.status_label.pack(side=tk.LEFT, padx=StyleManager.PADDING['default'])
        
        self.recording_label = ttk.Label(self, text="Not Recording",
                                        style=StyleManager.get_widget_style('label'))
        self.recording_label.pack(side=tk.RIGHT, padx=StyleManager.PADDING['default'])
    
    def set_status(self, text: str) -> None:
        self.status_label.config(text=text)
    
    def set_recording_status(self, is_recording: bool) -> None:
        text = "Recording" if is_recording else "Not Recording"
        self.recording_label.config(text=text)

class ToolTip:
    def __init__(self, widget: tk.Widget, text: str, delay: float = 0.5):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.id = None
        
        widget.bind('<Enter>', self.schedule)
        widget.bind('<Leave>', self.hide)
        widget.bind('<Button>', self.hide)

    def schedule(self, event=None):
        self.id = self.widget.after(int(self.delay * 1000), self.show)

    def show(self):
        x, y = get_widget_position(self.widget)
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack()

    def hide(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class ProgressSpinner(ttk.Frame):
    def __init__(self, master, size: int = 20):
        super().__init__(master)
        self.size = size
        self.canvas = tk.Canvas(self, width=size, height=size,
                              bg=self.master.cget('bg'), highlightthickness=0)
        self.canvas.pack()
        self.angle = 0
        self.is_spinning = False
        self._draw_spinner()
    
    def _draw_spinner(self):
        self.canvas.delete("spinner")
        x, y = self.size/2, self.size/2
        r = (self.size-4)/2
        start = self.angle
        extent = 120  # Draw 1/3 of circle
        
        # Draw arc with gradient color
        self.canvas.create_arc(2, 2, self.size-2, self.size-2,
                             start=start, extent=extent,
                             width=2, style="arc",
                             tags="spinner")
    
    def start(self):
        self.is_spinning = True
        self._spin()
    
    def stop(self):
        self.is_spinning = False
    
    def _spin(self):
        if not self.is_spinning:
            return
        self.angle = (self.angle + 10) % 360
        self._draw_spinner()
        self.after(50, self._spin)

class SearchableTextFrame(ttk.Frame):
    def __init__(self, master, height: int = 10, **kwargs):
        super().__init__(master, style=StyleManager.get_widget_style('frame'))
        
        # Search frame
        search_frame = ttk.Frame(self, style=StyleManager.get_widget_style('frame'))
        search_frame.pack(fill=tk.X, padx=StyleManager.PADDING['default'])
        
        ttk.Label(search_frame, text="Search:",
                 style=StyleManager.get_widget_style('label')).pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search_change)
        
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var,
                               style=StyleManager.get_widget_style('entry'))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                         padx=StyleManager.PADDING['default'])
        
        # Text area with scrollbar
        text_frame = ttk.Frame(self, style=StyleManager.get_widget_style('frame'))
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text = tk.Text(text_frame, height=height, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, command=self.text.yview)
        
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.configure(yscrollcommand=scrollbar.set)
    
    def _on_search_change(self, *args):
        """Handle search text changes"""
        search_text = self.search_var.get().lower()
        self.text.tag_remove('search', '1.0', tk.END)
        
        if search_text:
            idx = '1.0'
            while True:
                idx = self.text.search(search_text, idx, tk.END, nocase=True)
                if not idx:
                    break
                end_idx = f"{idx}+{len(search_text)}c"
                self.text.tag_add('search', idx, end_idx)
                idx = end_idx
            
            self.text.tag_config('search', background='yellow')
    
    def highlight_text(self, text: str, color: str = 'yellow') -> None:
        """Highlight specified text in the text widget"""
        self.text.tag_remove('highlight', '1.0', tk.END)
        
        if not text:
            return
            
        pos = '1.0'
        while True:
            pos = self.text.search(text, pos, tk.END, nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(text)}c"
            self.text.tag_add('highlight', pos, end_pos)
            pos = end_pos
            
        self.text.tag_config('highlight', background=color)
    
    def append_text(self, text: str, tags: tuple = ()) -> None:
        """Append text with optional tags"""
        self.text.insert(tk.END, text + '\n', tags)
        self.text.see(tk.END)

# Add keyboard shortcut support
class KeyboardShortcuts:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.shortcuts: Dict[str, Callable] = {}
        
    def add_shortcut(self, key: str, callback: Callable) -> None:
        """Add a keyboard shortcut"""
        self.shortcuts[key] = callback
        self.root.bind(f'<{key}>', lambda e: callback())
    
    def remove_shortcut(self, key: str) -> None:
        """Remove a keyboard shortcut"""
        if key in self.shortcuts:
            self.root.unbind(f'<{key}>')
            del self.shortcuts[key]
