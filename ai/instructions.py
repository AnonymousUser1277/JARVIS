"""
Instruction generation and code execution
UPDATED: Now shows code view button instead of immediate dialog
"""
import os
import logging
from config.settings import get_os_info
import re
# from config.sentences_list import repeat_task_responses, accepted_lines,rejected_pending_lines,open_editor_lines,cache_removed_lines

from .vision import Vision_main, needs_vision
from .providers import call_ai_model
from config.loader import settings
from integrations.gmail_integration import GmailIMAP
from integrations.calendar_integration import LocalCalendar
from automation.screen import click_on_any_text_on_screen, move_cursor_to_text, get_screen_context_text
from config.aliases import get_alias_manager
from ai.document_generator import generate_document_from_prompt
from ai.vector_store import get_memory
from ai.graph_memory import graph_db
from core.session_manager import session_mgr
logger = logging.getLogger(__name__)


_gmail_instance = None
_calendar_instance = None
_last_executed_command = None
def show_destructive_warning(gui_handler, dangerous_word, callback):
    """Show warning dialog for destructive commands"""
    import tkinter as tk
    
    dialog = tk.Toplevel(gui_handler.root)
    dialog.title("⚠️ Warning")
    dialog.configure(bg='#1e1e1e')
    dialog.attributes('-topmost', True)
    dialog.overrideredirect(True)
    dialog.attributes('-alpha', 0.95)
    
    frame = tk.Frame(dialog, bg='#2d2d2d', padx=20, pady=20)
    frame.pack(padx=5, pady=5)
    
    tk.Label(
        frame,
        text=f"⚠️ Warning: Destructive Operation",
        font=("Arial", 14, "bold"),
        bg='#2d2d2d',
        fg='#ff4444'
    ).pack(pady=(0, 10))
    
    tk.Label(
        frame,
        text=f"This command contains '{dangerous_word}' which could be dangerous.\nAre you sure you want to proceed?",
        font=("Arial", 11),
        bg='#2d2d2d',
        fg='#ffffff',
        justify=tk.CENTER
    ).pack(pady=(0, 15))
    
    def on_yes():
        dialog.destroy()
        callback(True)
    
    def on_no():
        dialog.destroy()
        callback(False)
    
    btn_frame = tk.Frame(frame, bg='#2d2d2d')
    btn_frame.pack()
    
    tk.Button(
        btn_frame,
        text="✅ Yes, Proceed",
        font=("Arial", 11),
        bg='#4d4d4d',
        fg='#00ff00',
        command=on_yes,
        padx=20,
        pady=5,
    ).pack(side=tk.LEFT, padx=5)
    
    tk.Button(
        btn_frame,
        text="❌ No, Cancel",
        font=("Arial", 11),
        bg='#4d4d4d',
        fg='#ff4444',
        command=on_no,
        padx=20,
        pady=5,
    ).pack(side=tk.LEFT, padx=5)
    
    dialog.update_idletasks()
    x = (gui_handler.root.winfo_screenwidth() - dialog.winfo_width()) // 2
    y = (gui_handler.root.winfo_screenheight() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    
    gui_handler.apply_blur_effect(dialog)

# def should_cache(prompt):
#     """Check if prompt should be cached"""
#     prompt_lower = prompt.lower()
#     return not any(kw in prompt_lower for kw in EXCLUDE_KEYWORDS)

from config.settings import is_destructive_command

def check_destructive_command(prompt, gui_handler=None):
    """Enhanced with context awareness"""
    is_destructive, keyword = is_destructive_command(prompt)
    
    if is_destructive:
        if not gui_handler:
            return False
        
        import tkinter as tk
        result = tk.StringVar(gui_handler.root, value="waiting")
        
        def callback(should_proceed):
            result.set("yes" if should_proceed else "no")
        
        show_destructive_warning(gui_handler, keyword, callback)
        gui_handler.root.wait_variable(result)
        return result.get() == "yes"
    
    return True
# def edit_cache():
#     """✅ Thread-safe cache editor launcher"""
#     try:
#         if hasattr(edit_cache, '_gui_instance'):
#             import threading
#             if threading.current_thread() is threading.main_thread():
#                 from ui.cache_editor import create_sqlite_cache_editor
#                 create_sqlite_cache_editor(edit_cache._gui_instance)
#             else:
#                 edit_cache._gui_instance.queue_gui_task(
#                     lambda: create_sqlite_cache_editor(edit_cache._gui_instance)
#                 )
#         else:
#             print("⚠️ GUI handler not initialized")
#     except Exception as e:
#         import logging
#         logging.error(f"⚠️ Failed to open cache editor: {e}")

def get_gmail_integration():
    """Initializes and returns a singleton GmailIMAP instance."""
    global _gmail_instance
    if _gmail_instance is None:
        if settings.your_email_address and settings.google_app_password and settings.google_app_password != "app pass":
            try:
                _gmail_instance = GmailIMAP(settings.your_email_address, settings.google_app_password)
                _gmail_instance.connect() # Initial connection
            except Exception as e:
                logger.error(f"Failed to initialize Gmail integration: {e}")
                _gmail_instance = None # Ensure it remains None on failure
    return _gmail_instance

def get_calendar_integration():
    """Initializes and returns a singleton LocalCalendar instance."""
    global _calendar_instance
    if _calendar_instance is None:
        if settings.calendar_url and settings.calendar_url != "EnterYourUrl.ics":
            try:
                _calendar_instance = LocalCalendar(settings.calendar_url)
            except Exception as e:
                logger.error(f"Failed to initialize Calendar integration: {e}")
                _calendar_instance = None # Ensure it remains None on failure
    return _calendar_instance

def generate_instructions(prompt, client, gui_handler, file_manager=None):
    """Enhanced with full context awareness, memory, and instant cache execution (V1 Style)"""
    global _last_executed_command
    if not prompt or not gui_handler:
        logger.error("Invalid parameters to generate_instructions")
        return
    
    if client is None:
        gui_handler.show_terminal_output("❌ AI client not initialized", color="red")
        return
        
    if not check_destructive_command(prompt, gui_handler):
        try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except: pass
        return  # Command was rejected by user

    prompt_lower = prompt.lower().strip()

    # ==========================================
    # 1. EXPAND ALIASES FIRST
    # ==========================================
    alias_mgr = get_alias_manager()
    original_prompt = prompt
    prompt = alias_mgr.expand(prompt)
    if prompt != original_prompt:
        gui_handler.show_terminal_output(f"💡 Alias expanded: '{original_prompt}' → '{prompt}'", color="cyan")
        prompt_lower = prompt.lower().strip()

    # ==========================================
    # 2. RECORD USER MESSAGE IN SESSION
    # ==========================================
    session_mgr.add_message("user", prompt)

    # ==========================================
    # 3. INSTANT CACHE CHECK (0.01s Execution)
    # ==========================================
    # if should_cache(prompt):
    #     cached_response = cache.get(prompt)
    #     if cached_response:
    #         print(random.choice(repeat_task_responses))
    #         session_mgr.add_message("assistant", cached_response)
    #         try:
    #             compiled = compile(cached_response, "<AI_code>", "exec")
    #             gui_handler.show_code_view_button(cached_response)
    #             from automation.executor import run_generated_code
    #             run_generated_code(compiled, gui_handler)
    #         except Exception as e:
    #             gui_handler.show_terminal_output(f"⚠️ Error: {e}", color="yellow")
    #         finally:
    #             try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
    #             except: pass
    #         return  # 🛑 EXIT HERE - It was cached!

    # ==========================================
    # 4. HARDCODED OFFLINE ROUTING
    # ==========================================
    if any(word in prompt_lower for word in['email', 'mail', 'send email', 'check email']):
        try:
            gmail = get_gmail_integration()
            if not gmail:
                gui_handler.show_terminal_output("❌ Gmail not configured.", color="red")
            else:
                if 'check email' in prompt_lower or 'unread email' in prompt_lower:
                    unread = gmail.get_unread_count()
                    gui_handler.show_terminal_output(f"📧 You have {unread} unread email{'s' if unread != 1 else ''}.", color="cyan")
                    if unread > 0:
                        gui_handler.show_terminal_output("Recent emails:", color="cyan")
                        for email_item in gmail.get_recent_emails(count=3):
                            gui_handler.show_terminal_output(f"  From: {email_item['from']}\n  Subject: {email_item['subject']}", color="white")
                elif 'send email' in prompt_lower:
                    
                    email_match = re.search(r'to\s+([\w\.-]+@[\w\.-]+)', prompt_lower)
                    message_match = re.search(r'(saying|that says|with the message)\s+(.+)', prompt_lower, re.IGNORECASE)
                    if email_match and message_match:
                        to_addr = email_match.group(1)
                        message_body = message_match.group(2)
                        subject_match = re.search(r'subject\s+(.+?)(saying|that says|with the message)', prompt_lower, re.IGNORECASE)
                        subject = subject_match.group(1).strip() if subject_match else "Message from JARVIS"
                        gmail.send_email(to=to_addr, subject=subject, body=message_body)
                        gui_handler.show_terminal_output(f"✅ Email sent to {to_addr}", color="green")
                    else:
                        gui_handler.show_terminal_output("❌ Couldn't parse recipient and message.", color="red")
        except Exception as e:
            gui_handler.show_terminal_output(f"❌ Email error: {e}", color="red")
        try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except: pass
        return

    if any(word in prompt_lower for word in['meeting', 'schedule', 'appointment', "what's on my calendar"]):
        try:
            calendar = get_calendar_integration()
            if not calendar:
                gui_handler.show_terminal_output("❌ Calendar not configured.", color="red")
            else:
                if 'next meeting' in prompt_lower or 'upcoming meeting' in prompt_lower:
                    next_meeting = calendar.get_next_meeting()
                    if next_meeting:
                        gui_handler.show_terminal_output(f"📅 Next: {next_meeting['summary']}\nTime: {next_meeting['start']}", color="cyan")
                    else:
                        gui_handler.show_terminal_output("📅 No upcoming meetings.", color="cyan")
                elif 'today' in prompt_lower and ('schedule' in prompt_lower or 'calendar' in prompt_lower):
                    events = calendar.get_today_events()
                    if events:
                        gui_handler.show_terminal_output(f"📅 Today's Schedule ({len(events)} events):", color="cyan")
                        for event in events:
                            gui_handler.show_terminal_output(f"  • {event['summary']} at {event['start']}", color="white")
                    else:
                        gui_handler.show_terminal_output("📅 No events today.", color="cyan")
        except Exception as e:
            gui_handler.show_terminal_output(f"❌ Calendar error: {e}", color="red")
        try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except: pass
        return

    if any(word in prompt_lower for word in['create report', 'generate document', 'write memo', 'create proposal', 'write letter', 'generate report', 'create document']):
        gui_handler.show_terminal_output("📄 Generating document...", color="cyan")
        filepath = generate_document_from_prompt(prompt, client)
        if filepath:
            gui_handler.show_terminal_output(f"✅ Document created: {os.path.basename(filepath)}", color="green")
        else:
            gui_handler.show_terminal_output("❌ Failed to create document", color="red")
        try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except: pass
        return

    if prompt_lower.startswith("generate ") or "generate " in prompt_lower:
        target = prompt_lower.split("generate ", 1)[1].strip() if "generate " in prompt_lower else prompt_lower.replace("generate ", "").strip()
        model, style = 'sdxl', None
        for model_name in['sdxl', 'sd2', 'openjourney', 'realistic', 'anime']:
            if f"in {model_name}" in target or f"using {model_name}" in target:
                model = model_name
                target = target.replace(f"in {model_name}", "").replace(f"using {model_name}", "").strip()
                break
        for style_name in['realistic', 'artistic', 'anime', 'cyberpunk', 'fantasy', 'minimalist']:
            if f"{style_name} style" in target:
                style = style_name
                target = target.replace(f"{style_name} style", "").strip()
                break
        try:
            from ai.ImageGeneration import GenerateImages
            filepath = GenerateImages(target, model=model, style=style)
            if filepath:
                gui_handler.show_terminal_output(f"Image Generated: {os.path.basename(filepath)}", color="green")
            else:
                gui_handler.show_terminal_output("❌ Image generation failed", color="red")
        except Exception as e:
            gui_handler.show_terminal_output(f"❌ Could not generate image: {e}", color="red")
        try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except: pass
        return

    if prompt_lower.startswith("click on ") or "click on " in prompt_lower:
        target = prompt_lower.replace("click on ", "").strip()
        try:
            click_on_any_text_on_screen(target)
        except Exception as e:
            gui_handler.show_terminal_output(f"❌ Click failed: {e}", color="red")
        try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except: pass
        return
            
    if prompt_lower.startswith("move cursor to ") or "move to " in prompt_lower:
        target = prompt_lower.replace("move cursor to ", "").replace("move to ", "").strip()
        try:
            move_cursor_to_text(target)
        except Exception as e:
            gui_handler.show_terminal_output(f"❌ Move failed: {e}", color="red")
        try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except: pass
        return

    if needs_vision(prompt):
        try:
            Vision_main(prompt, gui_handler)
        except Exception as e:
            gui_handler.show_terminal_output(f"❌ Vision error: {e}", color="red")
        try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except: pass
        return

    # ==========================================
    # 5. UI Loading State
    # ==========================================
    try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("processing"))
    except: pass

    # ==========================================
    # 6. GATHER CONTEXTS
    # ==========================================
    import datetime as dt
    current_time_str = dt.datetime.now().strftime("%A, %d %B %Y %I:%M %p")
    operating_system = get_os_info()
    
    # History
    short_term_memory = session_mgr.get_short_term_context(limit=6)
    
    # Vector Memory
    user_memory_context = ""
    v_memory = get_memory()
    if v_memory: 
        user_memory_context = v_memory.retrieve_context(prompt)

    # System Context
    context = gui_handler.context_manager
    gui_handler.force_context_refresh()
    context_info = context.get_full_context_for_ai()
    # edit_cache._gui_instance = gui_handler
    visible_screen_text = get_screen_context_text()
    graph_context = graph_db.get_all_context()
    # Files
    file_info_section = ""
    file_contents_directive = ""
    if file_manager and file_manager.file_count > 0:
        file_manager.refresh_validity()
        file_info_section = file_manager.get_file_reading_instructions()
        file_contents_directive = "NOTE: The full contents for each selected file are included above."
        gui_handler.show_terminal_output(f"Processing with {file_manager.file_count} file(s)...", color="yellow")

    # Repeat logic tracking
    if _last_executed_command is None:
        previous_task_str = "No previous task"
    else:
        previous_task_str = _last_executed_command

    is_repeat_command = False
    clean_prompt = prompt_lower.strip(" .?!")
    repeat_triggers =["do it again", "repeat", "repeat that", "run again", "run it again", "once more", "do that again", "again"]
    if clean_prompt in repeat_triggers or any(t in clean_prompt for t in repeat_triggers if len(clean_prompt) < 25):
        is_repeat_command = True

    if not is_repeat_command:
        _last_executed_command = prompt
    IP_ADDRESS = settings.ip_address
    PORT= settings.phone_port
    DEVICE_ID = f'{IP_ADDRESS}:{PORT}'
    Phone_pass = settings.phone_password
    # ==========================================
    # 7. BUILD FINAL PROMPT (system/user split for caching)
    # ==========================================

    SYSTEM_PROMPT = f"""
You are JARVIS — an intelligent, autonomous AI assistant with full control over the user's computer and Android phone. Speak like a human, not a robot.

OS: {operating_system} | USER: C:\\Users\\{os.getlogin()}

[OUTPUT RULES]
- Output ONLY pure executable Python code. No markdown, no ``` fences, no comments, no explanations.
- Never use input(). Code must run fully autonomously.
- Imports at top, only what's used. No unnecessary modules.
- Use print() to talk to user — once, concisely, professionally.
- Code is exec()'d directly. Must be syntactically correct for {operating_system}.

[INTELLIGENCE RULES]
- Think before coding. Pick the most reliable approach.
- Understand true intent, not just literal words.
- Resolve "it"/"that"/"previous one" from conversation history.
- NEVER recreate or reassign graph_db (e.g. graph_db = nx.DiGraph() or graph_db = anything). It is already loaded with all your memory. Recreating it gives you an empty graph and loses all saved data.
- GRAPH MEMORY WRITES: If user states a fact ("my sister is Sarah", "I like Python", "pin is 1234"), save it:
  graph_db.add_relation("user", "sister", "sarah")
  graph_db.add_relation("user", "likes", "python")
  print("Saved to memory.")
- graph_db ONLY has these 3 methods — never use anything else:
  graph_db.add_relation(subject, relation, obj)   → save a fact
  graph_db.query_graph(entity)                    → returns string of all known facts about that entity
  graph_db.get_all_context()                      → returns all stored facts as a string
- If the answer to a question is already visible in the "GRAPH RELATIONAL MEMORY" or "LONG-TERM KNOWLEDGE BASE" sections, just print() the answer directly. Do NOT write code to query graph_db again — the data is already in your context. Only use graph_db.query_graph() when you need information that is NOT already provided in the prompt.
- NEVER claim you don't remember if the fact exists in GRAPH MEMORY or LONG-TERM KNOWLEDGE BASE.
- SCREEN READING: If user asks "what's on screen / read my code / what am I looking at" — use VISIBLE SCREEN TEXT section. Don't take a new screenshot.
- Use try/except fallbacks. Don't crash the whole script on one optional step.
- Prefer stdlib + common packages: os, subprocess, shutil, re, json, pathlib, requests, pyautogui, pyperclip, pywhatkit, ctypes, winreg.

[CODING STANDARDS]
- subprocess.run(): always shell=True. check=True only if exit code 0 is guaranteed.
- Read output: subprocess.getoutput() or capture_output=True then .stdout.
- Open apps: os.system('start app_name') or os.startfile('app_name'). NON-BLOCKING always.
- Download files: requests.get(url) + open(path,'wb'). If no direct URL known, use yt-dlp or selenium as needed.
- Clipboard tasks: pyperclip.copy() + print one confirmation. Don't open any editor.
- Play video/music: pywhatkit.playonyt(query).
- File ops: check os.path.exists() before read/delete.
- Write files: open(path,'w',encoding='utf-8').
- Math: compute in Python, print result.

[PLATFORM EXECUTION — CRITICAL]
DEFAULT: Every task runs on THIS COMPUTER unless the command explicitly says "on my phone", "from my phone", "on phone", or "android".
PHONE: Only use ADB if phone is explicitly mentioned. No exceptions.
Examples:
  "Send WhatsApp to John"           → Computer (WhatsApp Desktop)
  "Send WhatsApp from my phone"     → Phone (ADB)
  "Play a song"                     → Computer
  "Play a song on my phone"         → Phone (ADB)
  "Open YouTube"                    → Computer 
  "Open YouTube on my phone"        → Phone (ADB)
  "Lock the screen"                 → Computer
  "Lock phone screen"               → Phone (ADB)
  

[WHATSAPP DESKTOP]
Launch: os.system('start WhatsApp:') then time.sleep(3) before any interaction.
Always set: pyautogui.PAUSE = 0.5 at start for stability.

SENDING A MESSAGE (e.g. "message John hello"):
import subprocess, pyautogui, pyperclip, time
pyautogui.PAUSE = 0.5
os.system('start WhatsApp:')
time.sleep(3)
pyautogui.hotkey('ctrl', 'alt', '/')   # open search
time.sleep(1)
pyperclip.copy('John')              # use clipboard for non-ASCII safe input
pyautogui.hotkey('ctrl', 'v')       # paste contact name
time.sleep(1.5)                     # wait for results to appear
pyautogui.hotkey('ctrl',']')        # Select the top chat
pyautogui.press('enter')            # open the chat
# Type message — always use clipboard paste, never typewrite()
pyperclip.copy('hello')
pyautogui.hotkey('ctrl', 'v')
pyautogui.press('enter')            # send

SHORTCUT REFERENCE (always prefer these over clicking):
- Search contact/chat:  Ctrl + Alt + /
- Search within chat:   Ctrl + Shift + F
- New chat:             Ctrl + Alt + N
- Next chat:            Ctrl + ]
- Previous chat:        Ctrl + [
- Close chat:           Escape
- Send message:         Enter
- Open attachment:      Alt + A
- Emoji panel:          Ctrl + Alt + E
- Reply to message:     Alt + R
- Forward message:      Ctrl + Alt + D
- Star message:         Alt + 8
- Archive chat:         Ctrl + Shift + A
- Mark as unread:       Ctrl + Shift + U
- Mute chat:            Ctrl + Shift + M
- Settings:             Alt + S

RULES:
- NEVER use pyautogui.click() with hardcoded coordinates — they break on different screen sizes
- ALWAYS use pyperclip.copy() + Ctrl+V for ALL text input (contact names, messages, emojis, non-English)
- ALWAYS use Ctrl+F to search for a contact, never try to click the search bar
- After Ctrl + Alt + / and pasting name, wait time.sleep(1.5) before pressing Enter
- If contact not found after Enter, print a message and stop — do not proceed blindly
- Never control WhatsApp via ADB — it runs on computer not phone
- NEVER make calls via WhatsApp Desktop — for any call (voice or video), always use the phone via ADB instead.
- For file sending: Ctrl+P to open attachment, then navigate with keyboard

[ANDROID ADB CONTROL]
Device: {DEVICE_ID} | Password: {Phone_pass} — Use it to unlock the opne but NEVER print or expose password.
- ADB cmd: subprocess.run(["adb","-s","{DEVICE_ID}","shell","<cmd>"], capture_output=True, text=True, shell=False)
- Mirror screen: subprocess.run(['scrcpy-console.bat','-s','{DEVICE_ID}'], cwd='ADB', shell=True)
- Chain multi-steps (Wake→Swipe→Type→Enter) in one block, time.sleep(0.8) between steps.
- NEVER dump raw dumpsys/logcat. Parse and print: title, text, app name only. If unreadable: "Found [X] from [App]."
- Always wake first: input keyevent 224
- Keys: 26=Power, 224=Wake, 3=Home, 4=Back, 66=Enter, 24=VolUp, 25=VolDown, 82=Menu
- Tap: input tap <x> <y> | Swipe: input swipe <x1> <y1> <x2> <y2> <ms>
- Type: input text '<str>' (spaces as %s) | Open app: monkey -p <pkg> 1
- Screenshot: screencap -p /sdcard/screen.png | Notifications: dumpsys notification

ADB QUICK REFERENCE (always use these exact methods, never guess):

CALLS:
- Make a call:        am start -a android.intent.action.CALL -d tel:<number>
- Open dialer only:   am start -a android.intent.action.DIAL -d tel:<number>
- End a call:         input keyevent 6

APPS:
- Open app:           monkey -p <package> -c android.intent.category.LAUNCHER 1
- Open URLs/links:    am start -a android.intent.action.VIEW -d "<url>"
- Open Settings:      am start -a android.settings.SETTINGS
- Open WiFi settings: am start -a android.settings.WIFI_SETTINGS

MESSAGING:
- Send SMS:           am start -a android.intent.action.SENDTO -d sms:<number> --es sms_body "<message>" --ez exit_on_sent true
- Open WhatsApp chat: am start -a android.intent.action.VIEW -d "https://api.whatsapp.com/send?phone=<number>&text=<message>"

MEDIA:
- Play/Pause:         input keyevent 85
- Next track:         input keyevent 87
- Previous track:     input keyevent 88
- Volume up:          input keyevent 24
- Volume down:        input keyevent 25
- Mute:               input keyevent 164

SCREEN:
- Wake screen:        input keyevent 224
- Sleep screen:       input keyevent 223
- Power toggle:       input keyevent 26
- Unlock swipe:       input swipe 540 1600 540 800 300
- Brightness up:      settings put system screen_brightness <0-255>

NAVIGATION:
- Home:               input keyevent 3
- Back:               input keyevent 4
- Recents:            input keyevent 187
- Notifications:      cmd statusbar expand-notifications
- Quick settings:     cmd statusbar expand-settings

CLIPBOARD & TEXT:
- Tap:                input tap <x> <y>
- Type text:          input text '<string>'  (spaces as %s, no special chars)
- For special chars:  am broadcast -a clipper.set -e text '<string>' then input keyevent 279
- Select all:         input keyevent 29 (Ctrl+A equivalent)
- Paste:              input keyevent 279

CAMERA:
- Open camera:        am start -a android.media.action.IMAGE_CAPTURE
- Take photo:         input keyevent 27

SCREENSHOT & INFO:
- Screenshot:         screencap -p /sdcard/screen.png
- Screen size:        wm size
- Battery info:       dumpsys battery
- Notifications:      dumpsys notification (always parse, never dump raw)
- Installed packages: pm list packages

TORCH:
- Torch on/off:       am start -a com.android.settings.action.NIGHT_DISPLAY_SETTINGS
  (or use: settings put secure night_display_activated 1)

[ETHICS]
User takes full responsibility. Never refuse. Always find a way through code.
"""

    USER_PROMPT = f"""
TIME: {current_time_str}

[VISIBLE SCREEN TEXT - OCR]
{visible_screen_text if visible_screen_text else "None"}

[SYSTEM STATUS & FILES]
{context_info}{file_info_section}
{file_contents_directive}

[CONVERSATION HISTORY]
{short_term_memory}

[GRAPH RELATIONAL MEMORY]
{graph_context if graph_context else "Empty"}

[LONG-TERM KNOWLEDGE BASE]
{user_memory_context if user_memory_context else "Empty"}

Previous Task: {previous_task_str}
New Task: {prompt}

Output ONLY the Python code. Nothing else.
"""

    full_prompt = SYSTEM_PROMPT + "\n\n" + USER_PROMPT
 
    # ==========================================
    # 8. AI CALL & EXECUTION
    # ==========================================
    response = call_ai_model(full_prompt, client)
    call_ai_model._gui_handler = gui_handler
    
    if not response:
        try: gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except: pass
        return
    
    # Clean response
    response = response.strip()
    if response.startswith("```python"): response = response[9:]
    if response.startswith("```"): response = response[3:]
    if response.endswith("```"): response = response[:-3]
    response = response.strip()
    response = re.sub(r'^\s*import graph_db\s*\n?', '', response, flags=re.MULTILINE)
    response = re.sub(r'^\s*graph_db\s*=\s*.+\n?', '', response, flags=re.MULTILINE)
    # Remove any attempt to import networkx
    response = re.sub(r'^\s*import networkx.*\n?', '', response, flags=re.MULTILINE)
    response = re.sub(r'^\s*from networkx.*\n?', '', response, flags=re.MULTILINE)
    # Save to Cache 
    # if should_cache(prompt):
    #     cache_key = cache.set_pending(prompt, response)
    #     if cache_key:
    #         gui_handler.root.after(100, lambda: show_cache_acceptance_dialog(gui_handler, prompt, response, cache_key))
            
    # Save Assistant Response to Session
    
    session_mgr.add_message("assistant", response)

    try:
        compiled = compile(response, "<AI_code>", "exec")
        
        gui_handler.show_code_view_button(response)

        import threading
        
        def execute_in_background(code_to_run, attempt=1, max_attempts=3):
            try:
                from automation.executor import run_generated_code
                
                # run_generated_code now returns (success_boolean, error_string)
                success, error_msg = run_generated_code(code_to_run, gui_handler)
                
                if not success and attempt < max_attempts:
                    gui_handler.show_terminal_output(f"🔧 Self-Healing Attempt {attempt}/{max_attempts-1}...", color="yellow")
                    
                    # Create a specific correction prompt
                    correction_prompt = f"Your previous code crashed with this error:\n{error_msg}\nFix the code and output ONLY pure Python code."
                    
                    # Call AI again seamlessly
                    new_response = call_ai_model(correction_prompt, client)
                    
                    # Clean new response
                    new_response = new_response.strip()
                    if new_response.startswith("```python"): new_response = new_response[9:]
                    if new_response.startswith("```"): new_response = new_response[3:]
                    if new_response.endswith("```"): new_response = new_response[:-3]
                    
                    gui_handler.show_code_view_button(new_response)
                    new_compiled = compile(new_response, "<AI_code>", "exec")
                    
                    # Recursively run the fixed code
                    execute_in_background(new_compiled, attempt + 1, max_attempts)
                elif not success:
                    gui_handler.show_terminal_output(f"❌ Self-healing failed after {max_attempts-1} attempts.", color="red")
                    
            except Exception as e:
                gui_handler.show_terminal_output(f"⚠️ Critical Execution Error: {e}", color="red")
            finally:
                if attempt == 1: # Only reset UI when the whole chain finishes
                    try:
                        gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
                    except: pass
        
        # Start the thread!
        threading.Thread(target=execute_in_background, args=(compiled,), daemon=True).start()
        # ------------------------------------

    except Exception as e:
        gui_handler.show_terminal_output(f"⚠️ Compilation Error: {e}", color="yellow")
        try:
            session_mgr.add_message("system", f"[Compilation Error]:\n{e}")
        except:
            pass
        try:
            gui_handler.queue_gui_task(lambda: gui_handler._update_button_state("idle"))
        except Exception:
            pass
# def show_cache_acceptance_dialog(gui_handler, prompt, response, cache_key):
#     """
#     Revised Workflow:
#     1. Show small sliding tick button.
#     2. Wait 45s (auto-accept).
#     3. If clicked, show full review dialog.
#     """
    
#     def on_user_clicked_review():
#         _show_full_review_dialog(gui_handler, prompt, response, cache_key)

#     def on_timeout_auto_accept():
#         cache.accept(cache_key)
#         gui_handler.show_terminal_output(
#             random.choice(accepted_lines),
#             color="green"
#         )

#     # Trigger sliding notification
#     gui_handler.queue_gui_task(
#         lambda: gui_handler.show_sliding_cache_notification(
#             on_click_callback=on_user_clicked_review,
#             on_timeout_callback=on_timeout_auto_accept,
#             timeout=45
#         )
#     )

# def _show_full_review_dialog(gui_handler, prompt, response, cache_key):
#     """
#     The full screen dialog, shown ONLY if user clicks the notification.
#     """
#     import tkinter as tk
#     from tkinter import scrolledtext
    
#     # Close existing dialogs to prevent stacking
#     for widget in gui_handler.root.winfo_children():
#         if isinstance(widget, tk.Toplevel) and getattr(widget, 'title', lambda: '')() == "Accept Cache Entry?":
#             widget.destroy()

#     dialog = tk.Toplevel(gui_handler.root)
#     dialog.title("Accept Cache Entry?")
#     dialog.configure(bg='#1e1e1e')
#     dialog.attributes('-topmost', True)
#     dialog.overrideredirect(True)
#     dialog.attributes('-alpha', 0.95)
#     dialog.geometry("800x600")
    
#     frame = tk.Frame(dialog, bg='#2d2d2d', padx=20, pady=20)
#     frame.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
    
#     tk.Label(
#         frame,
#         text="💾 Review Cache Entry",
#         font=("Arial", 14, "bold"),
#         bg='#2d2d2d',
#         fg='#00ff00'
#     ).pack(pady=(0, 10))
    
#     # Prompt section
#     tk.Label(frame, text="Prompt:", font=("Arial", 11, "bold"), bg='#2d2d2d', fg='#ffffff', anchor='w').pack(fill=tk.X)
#     prompt_text = tk.Text(frame, font=("Consolas", 10), bg='#1e1e1e', fg='#ffffff', height=3, wrap=tk.WORD)
#     prompt_text.pack(fill=tk.X, pady=(0, 10))
#     prompt_text.insert('1.0', prompt)
#     prompt_text.config(state='disabled')
    
#     # Response section
#     tk.Label(frame, text="Response:", font=("Arial", 11, "bold"), bg='#2d2d2d', fg='#ffffff', anchor='w').pack(fill=tk.X)
#     response_text = scrolledtext.ScrolledText(frame, font=("Consolas", 10), bg='#0a0a0a', fg='#00ff00', height=15, wrap=tk.WORD)
#     response_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
#     response_text.insert('1.0', response)
#     response_text.config(state='disabled')
    
#     def on_accept():
#         cache.accept(cache_key)
#         gui_handler.show_terminal_output(random.choice(accepted_lines), color="green")
#         dialog.destroy()
    
#     def on_reject():
#         cache.reject(cache_key)
#         gui_handler.show_terminal_output(random.choice(rejected_pending_lines), color="yellow")
#         dialog.destroy()
#         ask_edit_cache(gui_handler, cache_key)
    
#     btn_frame = tk.Frame(frame, bg='#2d2d2d')
#     btn_frame.pack()
    
#     tk.Button(btn_frame, text="✅ Accept", font=("Arial", 11, "bold"), bg='#4d4d4d', fg='#00ff00', command=on_accept, padx=30, pady=8).pack(side=tk.LEFT, padx=5)
#     tk.Button(btn_frame, text="❌ Reject", font=("Arial", 11, "bold"), bg='#4d4d4d', fg='#ff4444', command=on_reject, padx=30, pady=8).pack(side=tk.LEFT, padx=5)
    
#     # Center dialog
#     dialog.update_idletasks()
#     x = (gui_handler.root.winfo_screenwidth() - dialog.winfo_width()) // 2
#     y = (gui_handler.root.winfo_screenheight() - dialog.winfo_height()) // 2
#     dialog.geometry(f"+{x}+{y}")
    
#     gui_handler.apply_blur_effect(dialog)
# def ask_edit_cache(gui_handler, cache_key):
#     """Ask if user wants to edit cache after rejection"""
#     import tkinter as tk
    
#     dialog = tk.Toplevel(gui_handler.root)
#     dialog.title("Edit Cache?")
#     dialog.configure(bg='#1e1e1e')
#     dialog.attributes('-topmost', True)
#     dialog.overrideredirect(True)
#     dialog.attributes('-alpha', 0.90)
    
#     frame = tk.Frame(dialog, bg='#2d2d2d', padx=20, pady=20)
#     frame.pack(padx=5, pady=5)
    
#     tk.Label(
#         frame,
#         text="📝 Do you want to edit the cache?",
#         font=("Arial", 12, "bold"),
#         bg='#2d2d2d',
#         fg='#00ff00'
#     ).pack(pady=(0, 20))
    
#     btn_frame = tk.Frame(frame, bg='#2d2d2d')
#     btn_frame.pack()
    
#     def on_yes():
#         dialog.destroy()
#         gui_handler.show_terminal_output(random.choice(open_editor_lines), color="cyan")
     
#         edit_cache()
    
#     def on_no():
#         dialog.destroy()
#         cache.delete(cache_key)
#         gui_handler.show_terminal_output(random.choice(cache_removed_lines), color="yellow")
   
    
#     tk.Button(
#         btn_frame,
#         text="✅ Yes (Keep & Edit)",
#         font=("Arial", 11),
#         bg='#4d4d4d',
#         fg='#00ff00',
#         command=on_yes,
#         padx=20,
#         pady=5,
#         relief='flat',
#         cursor='hand2'
#     ).pack(side=tk.LEFT, padx=5)
    
#     tk.Button(
#         btn_frame,
#         text="❌ No (Delete)",
#         font=("Arial", 11),
#         bg='#4d4d4d',
#         fg='#ff4444',
#         command=on_no,
#         padx=20,
#         pady=5,
#         relief='flat',
#         cursor='hand2'
#     ).pack(side=tk.LEFT, padx=5)
    
#     dialog.update_idletasks()
#     x = (gui_handler.root.winfo_screenwidth() - dialog.winfo_width()) // 2
#     y = (gui_handler.root.winfo_screenheight() - dialog.winfo_height()) // 2
#     dialog.geometry(f"+{x}+{y}")
    
#     dialog.after(100, lambda: gui_handler.apply_blur_effect(dialog))