"""
Context monitoring system
"""
from config.loader import settings
from .explorer import explorer_path_monitor
from .browser import browser_url_monitor
from .clipboard import clipboard_monitor
from .window import window_title_monitor
from .monitor_controller import MonitorController
from .phone_notification import phone_notification_monitor
# from .whatsapp_monitor import whatsapp_desktop_monitor
from .system import (
    performance_monitor,
    battery_monitor,
    network_monitor,
    idle_monitor,
    downloads_monitor
)
from .devices import port_monitor, bluetooth_monitor
import threading
import logging
logger = logging.getLogger(__name__)


# Global controller
monitor_controller = MonitorController()

def start_all_monitors(context_manager):
    """Register tasks instead of starting raw threads"""

    # 1. Register polling monitors
    monitor_controller.register(performance_monitor,   settings.performance_poll,   context_manager)
    monitor_controller.register(battery_monitor,       settings.battery_poll,        context_manager)
    monitor_controller.register(idle_monitor,          settings.idle_time_poll,      context_manager)
    monitor_controller.register(downloads_monitor,     settings.downloads_poll,      context_manager)
    monitor_controller.register(network_monitor,       settings.network_poll,        context_manager)
    monitor_controller.register(port_monitor,          settings.usb_ports_poll,      context_manager)
    monitor_controller.register(bluetooth_monitor,     settings.bluetooth_poll,      context_manager)
    monitor_controller.register(explorer_path_monitor, settings.explorer_path_poll,  context_manager)
    monitor_controller.register(window_title_monitor,  settings.active_window_poll,  context_manager)

    # 2. Start the controller (1 thread total for all polling)
    monitor_controller.start()

    # 3. Event-driven monitors — dedicated threads

    # Clipboard: uses Windows message pump
    threading.Thread(
        target=clipboard_monitor,
        args=(context_manager,),
        daemon=True,
        name="Clipboard-Monitor"
    ).start()

    # Browser: relies on extension/uiauto
    threading.Thread(
        target=browser_url_monitor,
        args=(context_manager, settings.browser_url_poll),
        daemon=True,
        name="Browser-Monitor"
    ).start()

    # Phone notifications via ADB (everything except WhatsApp private)
    threading.Thread(
        target=phone_notification_monitor,
        args=(context_manager,),
        daemon=True,
        name="Phone-Notification-Monitor"
    ).start()

    # WhatsApp Desktop: reads Windows notification DB directly
    # threading.Thread(
    #     target=whatsapp_desktop_monitor,
    #     args=(context_manager,),
    #     daemon=True,
    #     name="WhatsApp-Desktop-Monitor"
    # ).start()

    logger.info("✅ Monitor Controller active: 9 polled + 3 event-based threads")
    print("✅ Monitor Controller active: 9 polled + 3 event-based threads")


__all__ = [
    'start_all_monitors',
    'explorer_path_monitor',
    'clipboard_monitor',
    'window_title_monitor',
    'performance_monitor',
    'battery_monitor',
    'network_monitor',
    'idle_monitor',
    'downloads_monitor',
    'port_monitor',
    'bluetooth_monitor',
    'phone_notification_monitor',
    # 'whatsapp_desktop_monitor',
]