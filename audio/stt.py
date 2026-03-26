import os
import time
import threading
import subprocess
import queue
from flask import Flask, render_template_string
from flask_socketio import SocketIO
from config.loader import settings
import logging
# Silence Werkzeug (Flask's server) logs completely
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) 
# If you still see logs, add:
os.environ['WERKZEUG_RUN_MAIN'] = 'true'
logger = logging.getLogger(__name__)

# This HTML is served to the background browser
HTML_STT_CODE = """
<!DOCTYPE html>
<html>
<body>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
    <script>
        const socket = io('http://127.0.0.1:5556', { transports: ['websocket'] });
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        
        recognition.continuous = true;
        recognition.interimResults = true; 
        recognition.lang = '{{ lang }}';

        recognition.onresult = (event) => {
            const lastIndex = event.results.length - 1;
            const text = event.results[lastIndex][0].transcript.trim();
            const isFinal = event.results[lastIndex].isFinal;
            
            // Send text and status to Python
            socket.emit('transcript', { text: text, isFinal: isFinal });
        };

        recognition.onend = () => { recognition.start(); };
        recognition.onerror = () => { recognition.start(); };
        socket.on('connect', () => { recognition.start(); });
    </script>
</body>
</html>
"""

class SpeechToTextListener:
    def __init__(self, website_path=None, language=settings.stt_language, gui_handler=None):
        self.gui_handler = gui_handler
        self.language = language
        self.transcript_queue = queue.Queue()
        self.is_listening = False
        self.wake_word_listening = False
        self.stop_listening = False

        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='eventlet')
        
        @self.app.route('/')
        def index(): return render_template_string(HTML_STT_CODE, lang=self.language)

        @self.socketio.on('transcript')
        def handle_transcript(data):
            self.transcript_queue.put(data)
    
        # Start server using eventlet
        self.server_thread = threading.Thread(target=lambda: self.socketio.run(
            self.app, 
            host='127.0.0.1', 
            port=5556, 
            allow_unsafe_werkzeug=True, 
            log_output=False,
            debug=False
        ), daemon=True)
        self.server_thread.start()
        
        self.browser_proc = None
        self._launch_browser()

    def _launch_browser(self):
        paths = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
        exe = next((p for p in paths if os.path.exists(p)), None)
        if exe:
            flags = [exe, "--headless=new", "--use-fake-ui-for-media-stream", "--disable-background-timer-throttling", "http://127.0.0.1:5556"]
            self.browser_proc = subprocess.Popen(flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _flush_queue(self):
        while not self.transcript_queue.empty():
            try: self.transcript_queue.get_nowait()
            except: break

    def stop_wake_word_listening(self):
        self.wake_word_listening = False

    def listen_for_wake_word(self, wake_word="jarvis"):
        self.wake_word_listening = True
        self._flush_queue()
        while self.wake_word_listening:
            try:
                data = self.transcript_queue.get(timeout=0.1)
                text = data.get('text', '').lower()
                if wake_word.lower() in text:
                    self.wake_word_listening = False
                    return True
            except queue.Empty: continue
        return False

    def listen(self, check_stop_words=False, stop_words=None):
        from config.settings import IGNORE_WORDS
        self.is_listening = True
        self.stop_listening = False
        self._flush_queue()
        print("\rListening...", end='', flush=True)

        current_text = ""
        last_heard_time = time.time()

        while not self.stop_listening:
            try:
                data = self.transcript_queue.get(timeout=0.1)
                text = data.get('text', '')
                is_final = data.get('isFinal', False)

                if text:
                    # Update local buffer
                    current_text = text
                    last_heard_time = time.time()
                    print(f"\rUser Speaking: {text}               ", end='', flush=True)

                # Return only if final OR silence for 1.5 seconds
                if current_text and (is_final or (time.time() - last_heard_time > 1.5)):
                    res = current_text.lower().strip()
                    
                    if any(res == w for w in IGNORE_WORDS):
                        current_text = ""
                        continue
                        
                    if check_stop_words and stop_words and any(w in res for w in stop_words):
                        self.is_listening = False
                        return "STOP_COMMAND"
                    
                    print(f"\n\rYOU SAID: {current_text}")
                    self.is_listening = False
                    return res

            except queue.Empty:
                # Catch the timeout silence case
                if current_text and (time.time() - last_heard_time > 1.5):
                    res = current_text.lower().strip()
                    if any(res == w for w in IGNORE_WORDS):
                        current_text = ""
                        continue
                    print(f"\n\rYOU SAID: {current_text}")
                    self.is_listening = False
                    return res
                continue
        
        self.is_listening = False
        return None

    def stop_recording(self): 
        self.stop_listening = True
        self.is_listening = False

    def clear_text(self): 
        self._flush_queue()

    def cleanup(self): 
        if self.browser_proc: self.browser_proc.kill()
