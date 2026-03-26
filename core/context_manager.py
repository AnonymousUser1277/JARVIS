"""
Optimized Context Manager with 500ms caching and event-driven updates
"""

import threading
import time
from typing import Dict, List, Tuple, Optional
import os
import logging

logger = logging.getLogger(__name__)


class CachedContext:
    """Cached context with TTL"""
    def __init__(self, data, timestamp):
        self.data = data
        self.timestamp = timestamp

    def is_expired(self, ttl: float = 0.5) -> bool:
        return (time.time() - self.timestamp) > ttl


class OptimizedContextManager:

    def __init__(self):
        self.lock = threading.RLock()
        self._shell_windows = None
        self.is_dirty = True
        self.cache_ttl = 0.5
        self._context_cache = None
        self._full_context_cache = None
        self._context_changed = threading.Event()
        self._last_update = 0

        self.current_url: Optional[str] = None
        self.current_folder: Optional[str] = None
        self.last_url: Optional[str] = None
        self.last_folder: Optional[str] = None

        self.clipboard_content: Optional[Tuple] = None
        self.clipboard_history: List[Tuple] = []
        self.active_window: Optional[str] = None
        self.window_history: List[Tuple] = []

        self.recent_downloads: List[str] = []
        self.known_downloads: set = set()

        self.cpu_percent: float = 0
        self.ram_percent: float = 0
        self.disk_percent: float = 0
        self.temperatures: Dict[str, float] = {'cpu': 0, 'gpu': 0}

        self.network_connected: bool = False
        self.wifi_ssid: Optional[str] = None
        self.connected_devices: Dict = {}
        self.bluetooth_devices: Dict = {}

        self.battery_percent: Optional[int] = None
        self.charging_status: Optional[str] = None

        self.idle_time: float = 0
        self.last_activity: float = time.time()
        self.webcam_active: bool = False

        logger.info("✅ Optimized Context Manager initialized")

    @property
    def active_window_title(self) -> Optional[str]:
        """Alias for active_window — for backward compatibility."""
        return self.active_window

    def _invalidate_cache(self):
        self._context_cache = None
        self._full_context_cache = None
        self._context_changed.set()
        self._last_update = time.time()

    def get_context_string(self) -> str:
        with self.lock:
            if self._context_cache and not self._context_cache.is_expired(self.cache_ttl):
                return self._context_cache.data

            parts = []
            if self.current_url:
                domain = self.current_url.split('/')[2] if self.current_url.count('/') >= 2 else self.current_url
                parts.append(f"Browser: {domain}")
            if self.current_folder:
                parts.append(f"Folder: {os.path.basename(self.current_folder)}")
            if self.clipboard_content:
                clip_type, clip_data = self.clipboard_content
                if clip_type == 'text':
                    parts.append(f"Clipboard: {clip_data[:50].replace(chr(10), ' ')}...")
            if self.active_window:
                parts.append(f"Active: {self.active_window}")
            if self.recent_downloads:
                parts.append(f"Downloaded: {self.recent_downloads[-1]}")
            if self.cpu_percent > 70 or self.ram_percent > 80:
                parts.append(f"⚠️ CPU {self.cpu_percent}%, RAM {self.ram_percent}%")
            if self.battery_percent is not None:
                parts.append(f"Battery: {self.battery_percent}%")
            if self.wifi_ssid:
                parts.append(f"WiFi: {self.wifi_ssid}")

            result = " | ".join(parts) if parts else "No context"
            self._context_cache = CachedContext(result, time.time())
            self.is_dirty = False
            return result

    def get_full_context_for_ai(self) -> str:
        with self.lock:
            if self._full_context_cache and not self._full_context_cache.is_expired(self.cache_ttl):
                return self._full_context_cache.data

            battery_str = f"{self.battery_percent}% ({self.charging_status})" if self.battery_percent is not None else "Unknown"
            network_str = f"{'Connected' if self.network_connected else 'Disconnected'}{f' ({self.wifi_ssid})' if self.wifi_ssid else ''}"

            result = f"""Active Window: {self.active_window or 'Unknown'}
Browser URL: {self.current_url or 'None'}
Open Folder: {self.current_folder or 'None'}
Clipboard: {self._format_clipboard()}
Last Download: {self.recent_downloads[-1] if self.recent_downloads else 'None'}
CPU: {self.cpu_percent}% | RAM: {self.ram_percent}% | Disk: {self.disk_percent}%
Battery: {battery_str} | Network: {network_str}

Context Rules (apply silently):
- "open this"/"bookmark this" → use Browser URL above
- "here"/"this folder"/"current directory" → use Open Folder above
- "this"/"clipboard" → use Clipboard above
- "close this" → use Active Window above
- "the download"/"that file" → use Last Download above
- High CPU/RAM → prefer lightweight operations"""

            self._full_context_cache = CachedContext(result, time.time())
            return result

    def _format_clipboard(self) -> str:
        if not self.clipboard_content:
            return "Empty"
        clip_type, clip_data = self.clipboard_content
        if clip_type == 'text':
            return f"Text: {str(clip_data)[:120].strip()}"
        elif clip_type == 'files':
            return f"Files: {', '.join(clip_data[:3])}"
        return "Image data"

    def update_url(self, url: str):
        with self.lock:
            self.is_dirty = True
            if url and url != self.current_url:
                self.last_url = self.current_url
                self.current_url = url
                self._invalidate_cache()

    def update_folder(self, folder: str):
        with self.lock:
            self.is_dirty = True
            if folder and folder != self.current_folder:
                self.last_folder = self.current_folder
                self.current_folder = folder
                self._invalidate_cache()

    def update_clipboard(self, content: Tuple):
        with self.lock:
            self.is_dirty = True
            if content and content != self.clipboard_content:
                self.clipboard_content = content
                self.clipboard_history.append((time.time(), content))
                if len(self.clipboard_history) > 50:
                    self.clipboard_history.pop(0)
                self._invalidate_cache()

    def update_window(self, window_title: str):
        with self.lock:
            self.is_dirty = True
            if window_title and window_title != self.active_window:
                self.active_window = window_title
                self.window_history.append((time.time(), window_title))
                if len(self.window_history) > 20:
                    self.window_history.pop(0)
                self._invalidate_cache()

    def update_performance(self, cpu: float, ram: float, disk: float):
        with self.lock:
            self.is_dirty = True
            changed = (
                abs(self.cpu_percent - cpu) > 5 or
                abs(self.ram_percent - ram) > 5 or
                abs(self.disk_percent - disk) > 5
            )
            self.cpu_percent = cpu
            self.ram_percent = ram
            self.disk_percent = disk
            if changed:
                self._invalidate_cache()

    def update_network(self, connected: bool, ssid: Optional[str] = None):
        with self.lock:
            self.is_dirty = True
            if self.network_connected != connected or self.wifi_ssid != ssid:
                self.network_connected = connected
                self.wifi_ssid = ssid
                self._invalidate_cache()

    def update_battery(self, percent: int, status: str):
        with self.lock:
            self.is_dirty = True
            changed = (
                self.battery_percent is None or
                abs(self.battery_percent - percent) > 5 or
                self.charging_status != status
            )
            self.battery_percent = percent
            self.charging_status = status
            if changed:
                self._invalidate_cache()

    def add_download(self, filename: str):
        with self.lock:
            if filename not in self.known_downloads:
                self.known_downloads.add(filename)
                self.recent_downloads.append(filename)
                if len(self.recent_downloads) > 10:
                    self.recent_downloads.pop(0)
                self._invalidate_cache()

    def update_device(self, device_id: str, device_info: Dict):
        with self.lock:
            self.is_dirty = True
            self.connected_devices[device_id] = device_info

    def remove_device(self, device_id: str):
        with self.lock:
            self.connected_devices.pop(device_id, None)

    def update_idle_time(self, idle_secs: float):
        with self.lock:
            self.is_dirty = True
            self.idle_time = idle_secs
            if idle_secs < 5:
                self.last_activity = time.time()

    def update_bluetooth_device(self, device_id, device_info):
        with self.lock:
            self.is_dirty = True
            self.bluetooth_devices[device_id] = device_info

    def remove_bluetooth_device(self, device_id):
        with self.lock:
            self.bluetooth_devices.pop(device_id, None)

    def wait_for_change(self, timeout: float = 1.0) -> bool:
        self._context_changed.clear()
        return self._context_changed.wait(timeout)


# Backward compatibility
ContextManager = OptimizedContextManager