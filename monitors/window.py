"""
Active window monitoring
Tracks the currently focused window
"""

import time
import win32gui
import logging
logger = logging.getLogger(__name__)
def get_active_window_title():
    """Get full title of active window"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            return win32gui.GetWindowText(hwnd)
    except:
        pass
    return None

def window_title_monitor(context_manager):
    """Monitor active window title"""
   
    try:
        title = get_active_window_title()
        if title and len(title) > 0:
            # Filter out system windows
            if title not in ['', 'Program Manager', 'Default IME', 'MSCTFIME UI']:
                context_manager.update_window(title)
    except Exception as e:
        logger.error(f"window title monitor error: {e}")
    