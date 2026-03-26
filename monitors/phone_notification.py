"""
Phone Notification Monitor - Receives from JARVIS Bridge Android app
The companion app on the phone forwards ALL notifications (including WhatsApp)
via HTTP POST to this server running on the PC.

Falls back to ADB dumpsys polling if the companion app is not connected.
"""
import threading
import time
import logging
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from utils.adb_utils import clean_adb_notification
from config.loader import settings
import subprocess

logger = logging.getLogger(__name__)

# ─── Shared state ────────────────────────────────────────────────────────────
seen_notifications = set()
_context_manager_ref = None
_companion_app_connected = False   # True once we receive from the Android app
_server_port = 9999

# ─── HTTP Handler (receives from companion app) ───────────────────────────────

class NotificationHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        global _companion_app_connected, seen_notifications

        if self.path != "/notification":
            self.send_response(404)
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))

            app   = data.get("app", "Unknown")
            title = data.get("title", "").strip()
            text  = data.get("text", "").strip()

            # Skip empty
            if not title and not text:
                self.send_response(200)
                self.end_headers()
                return

            notif = f"{app}"
            if title:
                notif += f" | {title}"
            if text:
                notif += f": {text}"

            # Dedup
            if notif not in seen_notifications:
                seen_notifications.add(notif)
                # Keep set from growing forever
                if len(seen_notifications) > 500:
                    seen_notifications = set(list(seen_notifications)[-250:])

                # print(f"📱 Phone Alert: {notif}")
                logger.info(f"📱 Phone Alert: {notif}")

                if _context_manager_ref:
                    try:
                        _context_manager_ref.last_phone_notification = notif
                    except Exception:
                        pass

            _companion_app_connected = True

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        except Exception as e:
            logger.error(f"📱 Notification handler error: {e}")
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default HTTP server logs (very noisy)
        pass


# def _start_http_server():
#     """Start the HTTP server that listens for notifications from the phone app."""
#     global _server_port
#     try:
#         server = HTTPServer(("0.0.0.0", _server_port), NotificationHandler)
#         logger.info(f"📱 JARVIS Bridge server listening on port {_server_port}")
#         # print(f"📱 JARVIS Bridge server started on port {_server_port}")
#         server.serve_forever()
#     except OSError as e:
#         logger.error(f"📱 Failed to start bridge server on port {_server_port}: {e}")
#         logger.error("📱 Falling back to ADB polling only")


# ─── ADB Fallback (polling dumpsys) ──────────────────────────────────────────

def _get_device_id():
    return f"{settings.ip_address}:{settings.phone_port}"

def _is_adb_connected(device_id):
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True, text=True, timeout=5
        )
        return device_id in result.stdout
    except Exception:
        return False

def _adb_fetch_and_alert():
    """Fallback: poll dumpsys for notifications (won't get WhatsApp private ones)."""
    global seen_notifications
    device_id = _get_device_id()
    try:
        raw = subprocess.check_output(
            ["adb", "-s", device_id, "shell", "dumpsys", "notification", "--noredact"],
            stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="ignore", timeout=10
        )
        current = set(clean_adb_notification(raw))
        new = current - seen_notifications
        seen_notifications = current

        for notif in new:
            print(f"📱 Phone Alert: {notif}")
            logger.info(f"📱 Phone Alert: {notif}")
            if _context_manager_ref:
                try:
                    _context_manager_ref.last_phone_notification = notif
                except Exception:
                    pass

    except subprocess.TimeoutExpired:
        logger.warning("📱 ADB dumpsys timed out")
    except Exception as e:
        logger.debug(f"📱 ADB fetch error: {e}")


def _adb_fallback_monitor():
    """
    Runs ADB logcat + dumpsys polling as a fallback.
    Only active when companion app is NOT connected.
    """
    device_id = _get_device_id()

    # Wait for ADB with retries
    for attempt in range(5):
        if _is_adb_connected(device_id):
            logger.info("✅ ADB connected (fallback mode)")
            break
        logger.warning(f"⚠️ ADB not found (attempt {attempt+1}/5), retrying in 5s...")
        time.sleep(5)

    # Initial snapshot
    _adb_fetch_and_alert()

    while True:
        # If companion app is connected, this fallback can sleep longer
        if _companion_app_connected:
            time.sleep(30)
            continue

        device_id = _get_device_id()
        if not _is_adb_connected(device_id):
            logger.warning("📱 ADB disconnected. Retrying in 10s...")
            time.sleep(10)
            continue

        try:
            process = subprocess.Popen(
                ["adb", "-s", device_id, "logcat", "-v", "brief"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="ignore"
            )

            for line in process.stdout:
                if _companion_app_connected:
                    process.kill()
                    break

                line_lower = line.lower()
                if any(k in line_lower for k in [
                    "enqueuenotification", "notification_enqueue",
                    "postnotification", "notificationmanager",
                    "newnotificationrecord",
                ]):
                    time.sleep(0.5)
                    _adb_fetch_and_alert()

        except Exception as e:
            logger.error(f"📱 ADB logcat error: {e} — retrying in 5s")
            time.sleep(5)


# ─── Main entry point ─────────────────────────────────────────────────────────

def phone_notification_monitor(context_manager):
    """
    Main entry point called from monitors/__init__.py.

    Starts two things in parallel:
    1. HTTP server — receives real notifications from JARVIS Bridge Android app
    2. ADB fallback — polls dumpsys (limited, no WhatsApp) if app not connected
    """
    global _context_manager_ref
    _context_manager_ref = context_manager

    logger.info("📱 Phone Notification Monitor starting...")
    # logger.info(f"📱 Waiting for JARVIS Bridge app on port {_server_port}...")
    # logger.info(f"📱 Make sure your phone's JARVIS Bridge app points to your PC IP on port {_server_port}")

    # # Start HTTP server in its own thread
    # http_thread = threading.Thread(
    #     target=_start_http_server,
    #     daemon=True,
    #     name="JarvisBridge-HTTP"
    # )
    # http_thread.start()

    # Run ADB fallback in this thread (blocking)
    _adb_fallback_monitor()