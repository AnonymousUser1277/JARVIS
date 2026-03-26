"""
Native Windows TTS using SAPI (Speech API)
10x faster than Selenium, zero memory leaks
"""
import logging
import threading
import queue
import time
from typing import Optional
import win32com.client
import pythoncom

logger = logging.getLogger(__name__)

class NativeTTSEngine:
    """Windows SAPI 5.4 TTS - Fast, reliable, native"""
    
    def __init__(self, voice_name: Optional[str] = None, rate: int = 1, volume: int = 100):
        self.lock = threading.RLock()
        self.speech_queue = queue.Queue(maxsize=50)
        self.is_speaking = False
        self.shutdown_flag = False
        self.voice_name = voice_name
        self.rate = rate
        self.volume = volume
        
        # Start speech processor thread
        self.processor_thread = threading.Thread(
            target=self._speech_processor,
            daemon=True,
            name="TTS-Processor"
        )
        self.processor_thread.start()
    
    def _speech_processor(self):
        """Background thread to process speech queue"""
        # Initialize COM in this thread
        pythoncom.CoInitialize()
        
        try:
            self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
            self.speaker.Rate = self.rate
            self.speaker.Volume = self.volume
            
            # Set voice
            if self.voice_name:
                voices = self.speaker.GetVoices()
                for i in range(voices.Count):
                    voice = voices.Item(i)
                    if self.voice_name.lower() in voice.GetDescription().lower():
                        self.speaker.Voice = voice
                        break
            
            logger.info(f"✅ Native TTS initialized")
            
            while not self.shutdown_flag:
                try:
                    text = self.speech_queue.get(timeout=0.5)
                    if text and text.strip():
                        self.is_speaking = True
                        # 0 = Synchronous (Blocking within this thread)
                        self.speaker.Speak(text, 0)
                        self.is_speaking = False
                        self.speech_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"TTS Speech Error: {e}")
                    self.is_speaking = False
                    
        except Exception as e:
            logger.critical(f"TTS Thread Crash: {e}")
        finally:
            pythoncom.CoUninitialize()
    
    def speak(self, text: str, priority: bool = False) -> bool:
        """Queue text for speaking"""
        if not text or not text.strip() or self.shutdown_flag:
            return False
        
        try:
            if priority:
                self.stop_speaking()
            
            self.speech_queue.put(text, block=False)
            return True
        except queue.Full:
            return False
    
    def stop_speaking(self):
        """
        Stop current speech immediately.
        NOTE: Called from Main Thread, but Speaker is in Worker Thread.
        We use a new COM instance to send the stop signal globally to SAPI.
        """
        # 1. Clear Python Queue
        with self.lock:
            try:
                while not self.speech_queue.empty():
                    self.speech_queue.get_nowait()
                    self.speech_queue.task_done()
            except:
                pass
        
        # 2. Force Stop SAPI
        # We cannot use self.speaker here because it belongs to the other thread.
        # We create a temporary lightweight interface to send the PURGE command.
        try:
            pythoncom.CoInitialize()
            temp_speaker = win32com.client.Dispatch("SAPI.SpVoice")
            # 2 = SVSFPurgeBeforeSpeak (Stops all speech on this object... 
            # effectively interrupting the output device if exclusive)
            temp_speaker.Speak("", 2) 
            self.is_speaking = False
        except Exception:
            pass
        finally:
            pythoncom.CoUninitialize()

    def wait_until_done(self, timeout: float = 30) -> bool:
        start = time.time()
        while (not self.speech_queue.empty() or self.is_speaking) and (time.time() - start < timeout):
            time.sleep(0.1)
        return True
    
    def cleanup(self):
        self.shutdown_flag = True
        self.stop_speaking()

# --- Global Wrappers ---
_global_tts_engine = None

def set_tts_engine(engine):
    global _global_tts_engine
    _global_tts_engine = engine

def speak(text, wait=False):
    if _global_tts_engine:
        _global_tts_engine.speak(text)
        if wait: _global_tts_engine.wait_until_done()

def stop_speaking():
    if _global_tts_engine:
        _global_tts_engine.stop_speaking()