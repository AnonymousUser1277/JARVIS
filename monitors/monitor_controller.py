import threading
import time
import logging

logger = logging.getLogger(__name__)

class MonitorController:
    def __init__(self):
        self.tasks = []
        self.stop_event = threading.Event()
        self._thread = None
        self.running = False

    def register(self, func, interval, *args):
        """Register a function to be polled at a specific interval (in seconds)."""
        self.tasks.append({
            'func': func,
            'interval': interval,
            'args': args,
            'last_run': 0
        })
        logger.info(f"✅ Registered monitor: {func.__name__} (every {interval}s)")

    def _loop(self):
        logger.info("🚀 Monitor Controller loop started")
        while not self.stop_event.is_set():
            now = time.time()
            for task in self.tasks:
                if now - task['last_run'] >= task['interval']:
                 
                    # print(f"DEBUG: Running task {task['func'].__name__}")
                    try:
                        task['func'](*task['args'])
                    except Exception as e:
                        logger.error(f"❌ Error in {task['func'].__name__}: {e}")
                    task['last_run'] = time.time()
            time.sleep(0.5)

    def start(self):
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._loop, daemon=True, name="Monitor-Controller")
            self._thread.start()

    def stop(self):
        self.stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("🛑 Monitor Controller stopped")