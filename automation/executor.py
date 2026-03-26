"""
Limitless Code Executor
Runs AI-generated code with full system access and auto-imports.
"""
import os
import sys
import types
import threading
import logging
import traceback
# Pre-import common libraries to make them available in the exec environment
import subprocess
import webbrowser
import time
import pyautogui
import json
import re
import datetime
import shutil
import random
import math
import ctypes
import pathlib

# Import TTS globally
from audio.tts import speak

logger = logging.getLogger(__name__)

def _get_script_path():
    try:
        return os.path.abspath(__file__)
    except NameError:
        return os.path.abspath(sys.argv[0])

SCRIPT_PATH = _get_script_path()

def run_generated_code(code, gui_handler, script_path=None):
    """
    Execute generated code with FULL permissions.
    """
    if script_path is None:
        script_path = SCRIPT_PATH

    # --- 1. Setup Output Capture ---
    original_print = print
    # We use a list to collect output for TTS
    printed_messages = []
    execution_output = []
    def speaking_print(*args, **kwargs):
        """
        Custom print:
        1. Sends to stdout (which gui.py redirects to Terminal UI).
        2. Captures text to speak it later.
        """
        # Create the message string
        message = ' '.join(str(arg) for arg in args)
        
        # 1. Print to real stdout. 
        # Because gui.py redirects sys.stdout to GuiLogger, this updates the UI.
        # NOW SAFE: GuiLogger will detect thread and use root.after()
        original_print(*args, **kwargs)
        
        # 2. Store for TTS
        if message.strip():
            printed_messages.append(message)
            execution_output.append(message)

    # --- 2. Prepare Environment ---
    exec_context = globals().copy()
    
    from ai.graph_memory import graph_db
    from core.file_indexer import file_indexer
    # Inject helpers
    exec_context.update({
        'gui_handler': gui_handler,
        'print': speaking_print,  # Inject our safe printer
        'speak': speak,           # Give AI direct access to TTS
        'graph_db': graph_db,
        'search_local_files': file_indexer.search,
        'exit': lambda: None,     # Disable exit
        'quit': lambda: None,
        '__file__': script_path,
        '__name__': '__main__',
    })

    try:
        import pyperclip
        exec_context['clipboard'] = pyperclip
        exec_context['pyperclip'] = pyperclip
    except ImportError:
        pass

    # --- 3. Execute ---
    try:
        if isinstance(code, str):
            compiled_code = compile(code, "<AI_Generated_Code>", "exec")
        else:
            compiled_code = code

        exec(compiled_code, exec_context)
        return True, None
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"⚠️ Code Execution Error:\n{tb}")
        
        if gui_handler:
            # This is now thread-safe via the fix in Step 1
            gui_handler.show_terminal_output(f"⚠️ Code crashed. Initiating self-healing...", color="yellow")
        return False, error_msg
        execution_output.append(error_msg)
    finally:
        # Save silent execution success to session memory (prints and errors are handled by Terminal UI)
        try:
            from core.session_manager import session_mgr
            if not execution_output:
                session_mgr.add_message("system", "[Execution completed without output]")
        except Exception as e:
            logger.error(f"Failed to save execution output to session: {e}")
        # --- 4. Cleanup & Auto-TTS ---
        
        # Reset UI Button State (Thread-safe)
        try:
            if hasattr(gui_handler, 'queue_gui_task'):
                gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except: pass

        # Restore Volume
        try:
            if hasattr(gui_handler, 'volume_controller'):
                gui_handler.volume_controller.restore_volume()
        except: pass

        # Speak the Output
        # We run this logic carefully to ensure it doesn't block the thread
        try:
            from config.settings import AUTO_TTS, ENABLE_TTS
            
            if ENABLE_TTS and AUTO_TTS and printed_messages:
                # Find the last valid message
                last_msg = None
                for txt in reversed(printed_messages):
                    if txt and str(txt).strip():
                        last_msg = str(txt).strip()
                        break
                
                if last_msg:
                    # Run speak in a daemon thread so executor finishes immediately
                    # and the TTS queue handles the speaking asynchronously
                    threading.Thread(
                        target=speak, 
                        args=(last_msg,), 
                        kwargs={'wait': False}, 
                        daemon=True
                    ).start()
                    
        except Exception as e:
            logger.error(f"Auto-TTS Error: {e}")