# 🤖 J.A.R.V.I.S
### Just A Rather Very Intelligent System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows)
![AI](https://img.shields.io/badge/AI-Multi--Provider-00ff00?style=for-the-badge)
![License](https://img.shields.io/badge/License-Personal%20Use-orange?style=for-the-badge)

**A fully autonomous, AI-powered desktop assistant with voice control, Android integration, computer automation, and persistent memory — built for Windows.**

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [AI Providers & Failover](#-ai-providers--failover)
- [Android (ADB) Integration](#-android-adb-integration)
- [Memory System](#-memory-system)
- [Monitors](#-monitors)
- [Integrations](#-integrations)
- [Voice Control](#-voice-control)
- [Project Structure](#-project-structure)
- [Hotkeys](#-hotkeys)
- [Contributing](#-contributing)

---

## 🧠 Overview

JARVIS is a Windows-native, voice-activated AI assistant that can control your entire computer and Android phone through natural language. It combines multiple AI backends with a rich context-awareness system — tracking your active window, clipboard, browser URL, file explorer path, downloads, battery, network, and more — to give the AI full situational awareness before executing any task.

The system generates and executes Python code autonomously in response to commands, with a self-healing loop that detects execution failures and asks the AI to fix them automatically.

---

## ✨ Features

### 🎙️ Voice & Input
- **Wake word detection** — say "Jarvis" to activate hands-free (configurable)
- **Continuous speech-to-text** via browser-based Web Speech API (Chrome/Edge headless)
- **Text input dialog** — `Win + Space` hotkey for typed commands
- **Command history** — navigate with arrow keys, reverse-search with `Ctrl+R`
- **Barge-in support** — speaking while JARVIS talks interrupts TTS immediately

### 🤖 AI & Execution
- **Multi-provider AI** with automatic failover: Groq → HuggingFace → OpenRouter → Mistral → Local Ollama
- **Self-healing code execution** — up to 3 automatic retry attempts on errors
- **Autonomous Python code generation & execution** with full system access
- **Offline fallback** to local Ollama model when internet is unavailable
- **Pre-warmed HTTP/2 connection pool** for reduced latency

### 📱 Android Control (ADB)
- Full Android device control over Wi-Fi via ADB
- Make/end calls, send SMS, open apps, control media
- Screen mirroring via scrcpy
- Phone notification monitoring (ADB + optional companion app)
- WhatsApp, camera, settings, brightness, torch, clipboard control

### 💾 Memory & Knowledge
- **Graph memory (SQLite)** — stores relational facts: `user → likes → Python`
- **Vector memory (FAISS)** — semantic similarity search over personal knowledge files (.txt, .csv)
- **Session memory** — short-term conversation context across turns
- **File indexer** — background SQLite index of Documents, Downloads, Desktop

### 👁️ Vision
- **Gemini-powered screen analysis** — answers questions about what's on screen using OCR + Gemini
- **Webcam capture** — can describe what the camera sees on demand
- **OCR screen context** — Tesseract reads screen text silently before every AI call

### 🖥️ Computer Automation
- Open/close apps, type, click, scroll, hotkeys via PyAutoGUI
- Click on any text visible on screen using OCR detection
- Clipboard read/write, file operations, process management
- WhatsApp Desktop control via keyboard shortcuts (no coordinate clicking)

### 🗓️ Scheduling & Integrations
- **Task scheduler** with natural language parsing ("remind me in 2 hours", "every day at 9 AM")
- **Gmail integration** — check unread count, read emails, send emails
- **Calendar integration** — iCal/ICS URL support for upcoming events
- **Document generation** — create .docx, .md, or .txt reports from prompts
- **Image generation** — Stable Diffusion via HuggingFace (SDXL, Realistic, Anime, etc.)

### 🔔 Proactive Notifications
- Low/full battery alerts
- Download completion notifications with file type detection
- Network connect/disconnect alerts
- USB and Bluetooth device connection events
- High CPU/RAM usage warnings
- Webcam activation detection

### 🎨 UI & Themes
- Animated JARVIS orb (idle pulse, listening, processing states)
- Floating terminal messages that fade with hover-to-pause
- System tray with full menu
- 4 built-in themes: Dark, Light, Matrix, Cyberpunk
- Multi-monitor support with user-selectable preferred display
- Settings dialog with live config.ini editing
- Command alias editor
- AI instruction prompt editor (edit SYSTEM_PROMPT and USER_PROMPT from UI)

---

## 🏗️ Architecture

```
JARVIS/
│
├── main.py                  ← Entry point, startup sequence
│
├── ai/                      ← AI layer
│   ├── providers.py         ← Multi-provider AI caller with failover
│   ├── instructions.py      ← Prompt builder & code executor dispatcher
│   ├── vector_store.py      ← FAISS semantic memory
│   ├── graph_memory.py      ← SQLite relational knowledge graph
│   ├── vision.py            ← Screen/camera capture + Gemini analysis
│   ├── ImageGeneration.py   ← HuggingFace image generation
│   ├── document_generator.py← .docx / .md / .txt generation
│   ├── connection_pool.py   ← HTTP/2 pre-warmed connections
│   ├── task_queue.py        ← Parallel AI task processor
│   └── proactive.py        ← Proactive suggestion engine
│
├── audio/                   ← Voice layer
│   ├── stt.py               ← Web Speech API via Flask + headless browser
│   ├── tts.py               ← TTS wrapper
│   ├── tts_native.py        ← Windows SAPI 5.4 native TTS engine
│   ├── volume.py            ← System volume controller
│   └── coordinator.py       ← STT/TTS conflict prevention + barge-in
│
├── automation/              ← System automation
│   ├── executor.py          ← Safe Python code executor
│   ├── hotkeys.py           ← Global hotkey manager (pynput)
│   └── screen.py            ← OCR click/move + screen context reader
│
├── core/                    ← Core services
│   ├── context_manager.py   ← Aggregates all live system context
│   ├── session_manager.py   ← Conversation history (per-session JSON)
│   ├── task_scheduler.py    ← Persistent SQLite task scheduler
│   ├── file_indexer.py      ← Background file index (SQLite)
│   ├── local_server.py      ← HTTP server for browser extension
│   └── notification.py      ← Proactive alert dispatcher
│
├── monitors/                ← Background context monitors
│   ├── system.py            ← CPU, RAM, battery, network, idle, downloads
│   ├── window.py            ← Active window title
│   ├── clipboard.py         ← Event-driven clipboard (Windows messages)
│   ├── browser.py           ← Browser URL (extension + UI automation fallback)
│   ├── explorer.py          ← File Explorer path
│   ├── devices.py           ← USB / HDMI / Bluetooth devices
│   ├── phone_notification.py← ADB notification poller + HTTP bridge server
│   └── monitor_controller.py← Single-thread polling loop for all monitors
│
├── integrations/            ← External services
│   ├── gmail_integration.py ← IMAP/SMTP Gmail
│   └── calendar_integration.py ← iCal calendar reader
│
├── ui/                      ← User interface
│   ├── gui.py               ← Main GUI handler, JARVIS orb
│   ├── terminal.py          ← Floating fade-out message terminal
│   ├── dialogs.py           ← Input dialog, response dialog
│   ├── settings_dialog.py   ← Live settings editor (auto-updates code)
│   ├── tray.py              ← System tray icon & menu
│   ├── theme_manager.py     ← Theme system
│   ├── startup.py           ← Startup splash screen
│   └── ...                  ← Alias editor, monitor selector, suggestion panel
│
├── config/                  ← Configuration
│   ├── loader.py            ← config.ini loader (single Config class)
│   ├── settings.py          ← Constants, path setup, destructive command detection
│   ├── api_keys.py          ← .env key loader
│   └── aliases.py           ← Command alias manager
│
└── utils/                   ← Utilities
    ├── setup_wizard.py      ← First-time setup GUI wizard
    ├── adb_utils.py         ← ADB notification parser
    ├── file_manager.py      ← Selected files handler for prompts
    ├── file_watcher.py      ← Dev mode auto-restart on file save
    ├── logger.py            ← Rotating file logger + GuiLogger
    └── helpers.py           ← Restart / shutdown helpers
```

---

## 📋 Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | 64-bit recommended |
| Windows | 10/11 | Required (uses Win32 APIs) |
| Google Chrome or Edge | Latest | For headless STT engine |
| Tesseract OCR | 5.x | For screen reading & click-on-text |
| ADB (Android Debug Bridge) | Any | Only for phone control features |
| scrcpy | Any | Only for screen mirroring |
| Ollama (optional) | Any | Local AI fallback when offline |

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/JARVIS.git
cd JARVIS
```

### 2. Run the setup wizard (recommended)

On first launch, JARVIS automatically opens an interactive setup wizard:

```bash
python main.py
```

The wizard will:
- Install all Python dependencies from `requirements.txt`
- Download and install Tesseract OCR
- Guide you through API key entry
- Generate `.env` and `config.ini`
- Optionally add JARVIS to Windows startup

### 3. Manual installation (advanced)

```bash
pip install -r requirements.txt
```

Then manually create `.env` and `config.ini` (see [Configuration](#-configuration)).

---

## ⚙️ Configuration

### `.env` — API Keys

Create a `.env` file in the project root:

```env
# AI Providers (at least one required)
GROQ_KEY_1=gsk_...
GROQ_KEY_2=gsk_...           # Optional backup key
GROQ_KEY_3=gsk_...           # Optional backup key

HUGGINGFACE_KEY_1=hf_...
HUGGINGFACE_KEY_2=hf_...
HUGGINGFACE_KEY_3=hf_...

OPENROUTER_KEY_1=sk-or-...
MISTRAL_KEY_1=...

# Vision (for screen/camera analysis)
GEMINI_KEY_1=AIza...
GEMINI_KEY_2=AIza...
GEMINI_KEY_3=AIza...

# Web search (optional)
TAVILY_API_KEY=tvly-...
```

### `config.ini` — System Settings

```ini
[Paths]
Program_path = C:\path\to\JARVIS
tesseract_cmd = C:\Program Files\Tesseract-OCR\tesseract.exe

[Audio]
enable_stt = true
enable_tts = true
stt_language = en-IN
TTS_Voice = Ryan
Wake_word = jarvis

[Behavior]
confirm_ai_execution = false
auto_tts_output = true
notifier_grace_period = 50.0
TERMINAL_MAX_MESSAGES = 5.0
TERMINAL_MESSAGE_LIFETIME = 8000.0
dev_mode = false
hide_console_window = true

[Monitors]
browser_url_poll = 1.0
explorer_path_poll = 1.0
clipboard_poll = 2.0
active_window_poll = 1.0
downloads_poll = 2.0
performance_poll = 10.0
idle_time_poll = 10.0
network_poll = 5.0
usb_ports_poll = 5.0
bluetooth_poll = 5.0
battery_poll = 10.0
phone_notification_poll = 10.0

[Integrations]
calendar_url = https://your-calendar-url.ics
google_app_password = your_app_password
your_email_address = you@gmail.com

[Adroid (ADB)]
ip_address = 192.168.1.100
phone_port = 5555
phone_password = 1234
```

> **Tip:** All settings can be edited through the GUI via System Tray → ⚙️ Settings without touching files.

---

## 🎮 Usage

### Starting JARVIS

```bash
# Standard launch (uses Jarvis.bat on Windows for ADB setup + admin privileges)
Jarvis.bat

# Or directly:
python main.py
```

### Giving Commands

**Via voice:** Say the wake word (`jarvis`) then speak your command.

**Via keyboard:** Press `Win + Space` to open the input dialog.

### Example Commands

```
# Computer control
"Open Spotify and play lo-fi music"
"Take a screenshot and save it to Downloads"
"Search for Python tutorials on YouTube"
"What's my CPU usage?"
"Set volume to 50%"

# File operations
"Create a report about quarterly sales performance"
"Find all PDF files in my Downloads folder"
"Read the content of the file I selected"

# Android phone control
"Call mom on my phone"
"Send WhatsApp to John saying I'll be late"
"Take a screenshot on my phone"
"Lock my phone screen"
"Play the next song on my phone"

# Memory
"My sister's name is Sarah"           # Saved to graph memory
"What's my sister's name?"            # Retrieved from memory
"Remember that my PIN is 1234"        # Stored as fact

# Vision
"What do you see?"                     # Screen + Gemini analysis
"What's on my screen?"

# Productivity
"Check my unread emails"
"What's on my calendar today?"
"Remind me to call John in 2 hours"
"Schedule a daily backup every day at 11 PM"

# Image generation
"Generate a cyberpunk cityscape in anime style"
"Generate a realistic portrait using realistic model"

# Documents
"Write a professional memo about the team meeting"
"Create a report on climate change"
```

---

## 🔄 AI Providers & Failover

JARVIS cycles through providers automatically when one fails or hits rate limits:

```
Groq (llama-3.3-70b-versatile)
  ↓ on failure
HuggingFace (Qwen2.5-Coder-32B-Instruct)
  ↓ on failure
OpenRouter (deepseek/deepseek-chat)
  ↓ on failure
Mistral (codestral-latest)
  ↓ on failure
Ollama (local, offline) ← also triggered automatically when no internet
```

Multiple API keys per provider are supported. On rate-limit errors, JARVIS switches to the next key before escalating to the next provider.

A toast notification appears in the terminal when a provider switch occurs.

---

## 📱 Android (ADB) Integration

### Setup

1. Enable **USB Debugging** on your Android device (Settings → Developer Options)
2. Connect via USB and run `Jarvis.bat` — it handles `adb tcpip 5555` automatically
3. Set your phone's IP address in `config.ini` under `[Adroid (ADB)]`
4. Subsequent launches connect over Wi-Fi without USB

### Supported Operations

| Category | Commands |
|---|---|
| **Calls** | Make call, end call, open dialer |
| **Messaging** | Send SMS, open WhatsApp chat |
| **Media** | Play/pause, next/previous track, volume |
| **Screen** | Wake, sleep, unlock, brightness, screenshot |
| **Navigation** | Home, back, recents, notifications, quick settings |
| **Apps** | Open any app by package name, open URLs |
| **Camera** | Open camera, take photo |
| **System** | Battery info, installed packages, screen size |
| **Mirroring** | Full screen mirror via scrcpy |

> **Note:** Commands default to the **computer** unless you explicitly say "on my phone" / "from my phone". E.g., `"Send WhatsApp to John"` uses WhatsApp Desktop; `"Send WhatsApp to John from my phone"` uses ADB.

---

## 🧠 Memory System

JARVIS has three layers of memory:

### 1. Graph Memory (Relational Facts)
Persistent SQLite database of subject-relation-object triples.

```python
# Automatically triggered when you state facts:
"My dog's name is Max"       → graph_db.add_relation("user", "dog", "max")
"I work at Google"           → graph_db.add_relation("user", "works at", "google")
"My birthday is March 5"     → graph_db.add_relation("user", "birthday", "march 5")
```

All stored facts are injected into every AI prompt automatically.

### 2. Vector Memory (Semantic Search — FAISS)
Place `.txt` or `.csv` files in `Data/learning_data/` to give JARVIS long-term personal knowledge.

- `.txt` files: plain text facts, notes, preferences
- `.csv` files: structured data with columns `Category, Entity, Value, Context`

The 6 most semantically relevant chunks are retrieved per query using MMR (Maximal Marginal Relevance).

### 3. Session Memory
Short-term in-session conversation history (last 6 turns) for context resolution. Saved as JSON in `Data/chat_sessions/`.

---

## 📊 Monitors

All monitors run in background threads and feed into the `ContextManager`, which is injected into every AI prompt:

| Monitor | What it tracks | Method |
|---|---|---|
| **Window** | Active window title | Win32 API polling |
| **Clipboard** | Text, files, images | Windows event-driven |
| **Browser URL** | Current tab URL | Chrome extension + UI Automation fallback |
| **Explorer** | Current folder path | Shell.Application COM |
| **Performance** | CPU %, RAM %, Disk % | psutil |
| **Battery** | Percent + charging status | psutil |
| **Network** | Connected + Wi-Fi SSID | socket + netsh |
| **Idle Time** | Seconds since last input | Win32 `GetLastInputInfo` |
| **Downloads** | New files in ~/Downloads | Directory diff |
| **USB/HDMI** | Connected devices | WMI Win32_PnPEntity |
| **Bluetooth** | Connected BT devices | WMI |
| **Phone Notifications** | Android notifications | ADB dumpsys + logcat |

---

## 🔌 Integrations

### Gmail
- Configure `google_app_password` and `your_email_address` in `config.ini`
- Commands: "Check my email", "How many unread emails?", "Send email to X saying Y"

### Calendar (iCal)
- Supports any `.ics` URL (Google Calendar, Outlook, Apple Calendar)
- Set `calendar_url` in `config.ini`
- Commands: "What's on my calendar today?", "When is my next meeting?"

### Browser Extension
- Install the Chrome extension from `browser_extention/`
- Sends active tab URL to JARVIS over `localhost:8989`
- Enables commands like "Bookmark this page", "Open this in a new tab"

---

## 🎤 Voice Control

JARVIS uses the browser's Web Speech API (Chrome/Edge) running headlessly for STT — no cloud API keys needed for voice input.

**TTS** uses Windows SAPI 5.4 natively (`NativeTTSEngine`) for zero-latency speech with no memory leaks. The default voice is configurable via `TTS_Voice` in `config.ini` (e.g., `Ryan` for Microsoft Ryan).

### STT Flow

```
Headless Chrome/Edge → Flask/SocketIO → SpeechToTextListener → generate_instructions()
```

### Audio Coordination

The `AudioCoordinator` prevents STT/TTS conflicts:
- Waits up to 5 seconds for STT to finish before TTS speaks
- Barge-in: if you speak while JARVIS is talking, TTS stops immediately
- Volume auto-lowers to 5% while listening, restores after

---

## 📁 Project Structure

```
JARVIS/
├── .env                     ← API keys (not in git)
├── config.ini               ← System settings (not in git)
├── Jarvis.bat               ← Windows launcher (ADB setup + admin + python main.py)
├── main.py                  ← Application entry point
├── requirements.txt         ← Python dependencies
│
├── ai/                      ← AI providers, memory, vision, generation
├── audio/                   ← STT, TTS, volume control
├── automation/              ← Code execution, hotkeys, screen OCR
├── browser_extention/       ← Chrome extension (manifest v3)
├── config/                  ← Settings loader, API keys, aliases
├── core/                    ← Context manager, scheduler, session, notifications
├── integrations/            ← Gmail, Calendar
├── monitors/                ← All background context monitors
├── ui/                      ← GUI, terminal, dialogs, tray, themes
└── utils/                   ← Setup wizard, logger, file watcher, helpers
│
└── Data/                    ← Runtime data (not in git)
    ├── chat_sessions/       ← Saved conversation histories
    ├── faiss_index/         ← Vector memory index
    ├── learning_data/       ← Personal knowledge (.txt, .csv)
    ├── History/             ← Command history
    ├── logs/                ← Rotating log files
    ├── graph_memory.db      ← Relational knowledge graph
    ├── file_index.db        ← Local file index
    └── scheduled_tasks.db   ← Persistent task scheduler
```

---

## ⌨️ Hotkeys

| Hotkey | Action |
|---|---|
| `Win + Space` | Toggle text input dialog |
| `Win + Enter` | Toggle microphone |
| `Alt + Shift + C` | View last generated code |

---

## 🛠️ Development Mode

Set `dev_mode = true` in `config.ini` to enable the file watcher. Any `.py` file saved in the project directories triggers an automatic restart of JARVIS — no manual relaunching needed during development.

---

## 📦 Key Dependencies

```
groq                    — Groq AI API client
langchain-huggingface   — HuggingFace embeddings
langchain-community     — FAISS vector store
faiss-cpu               — Semantic search
sentence-transformers   — Embedding model (all-MiniLM-L6-v2)
google-generativeai     — Gemini vision API
huggingface-hub         — Image generation inference
python-docx             — Word document generation
pyautogui               — GUI automation
pytesseract             — OCR screen reading
pynput                  — Global hotkeys
pystray                 — System tray
flask + flask-socketio  — STT browser communication
win32com / pywin32      — Windows COM APIs
pycaw                   — Windows audio volume control
psutil                  — System metrics
wmi                     — Device monitoring
mss                     — Fast screen capture
dateparser              — Natural language date parsing
watchdog                — Dev mode file watcher
```

---

## ⚠️ Disclaimer

JARVIS executes AI-generated Python code with full system access. It is designed for personal use on your own machine. You are fully responsible for any commands you give and their outcomes. Destructive commands (delete, format, wipe, etc.) trigger a confirmation dialog before execution.

---

## 🤝 Contributing

1. Fork the repository
2. Enable dev mode (`dev_mode = true`) for auto-restart on file save
3. Make your changes
4. Test thoroughly — the self-healing executor will surface most runtime errors
5. Submit a pull request

---

<div align="center">

**Built with ❤️ for the love of automation**

*"Sometimes you gotta run before you can walk." — Tony Stark*

</div>
