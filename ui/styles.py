import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

class StyleManager:
    FONTS = {
        'default': ('Arial', 10),
        'heading': ('Arial', 12, 'bold'),
        'monospace': ('Courier', 10),
        'small': ('Arial', 8),
        'large': ('Arial', 14, 'bold')
    }

    PADDING = {
        'small': 2,
        'default': 5,
        'large': 10
    }

    @staticmethod
    def configure_styles(theme: Dict[str, Any]) -> None:
        style = ttk.Style()
        
        # Configure common styles
        style.configure('App.TFrame', background=theme['bg'])
        style.configure('App.TLabel', 
                       background=theme['bg'], 
                       foreground=theme['fg'],
                       font=StyleManager.FONTS['default'])
                       
        # Button styles
        style.configure('App.TButton',
                       padding=StyleManager.PADDING['default'],
                       font=StyleManager.FONTS['default'])
                       
        style.configure('Primary.TButton',
                       background=theme['accent'],
                       foreground=theme['fg'])
                       
        style.configure('Warning.TButton',
                       background=theme['warning'],
                       foreground=theme['fg'])
                       
        # Entry styles
        style.configure('App.TEntry',
                       fieldbackground=theme['input_bg'],
                       foreground=theme['fg'])
                       
        # Heading styles
        style.configure('Heading.TLabel',
                       font=StyleManager.FONTS['heading'],
                       padding=StyleManager.PADDING['large'])

    @staticmethod
    def get_widget_style(widget_type: str, variant: str = 'default') -> str:
        """Returns the appropriate style name for a widget"""
        style_map = {
            'frame': {
                'default': 'App.TFrame'
            },
            'label': {
                'default': 'App.TLabel',
                'heading': 'Heading.TLabel'
            },
            'button': {
                'default': 'App.TButton',
                'primary': 'Primary.TButton',
                'warning': 'Warning.TButton'
            },
            'entry': {
                'default': 'App.TEntry'
            }
        }
        return style_map.get(widget_type, {}).get(variant, f'App.T{widget_type.capitalize()}')
