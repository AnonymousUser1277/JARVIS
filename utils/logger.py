"""
Enhanced logging system with proper levels and filtering
"""
import logging
import sys
import io
from datetime import datetime
from logging.handlers import RotatingFileHandler
from config.settings import LOG_DIR

class ColoredFormatter(logging.Formatter):
    """Colored console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class ExcludedMessagesFilter(logging.Filter):
    """Filter out noisy log messages"""
    
    EXCLUDED_PATTERNS = [
        "User Speaking:",
        "YOU SAID:",
        "Listening...",
        "🎤 Listening for",
        "Processing...",
    ]
    
    def filter(self, record):
        message = record.getMessage()
        return not any(pattern in message for pattern in self.EXCLUDED_PATTERNS)


def setup_logging(level=logging.INFO):
    """Setup comprehensive logging system"""
    log_dir = LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    main_log = log_dir / f"{today}.log"
    error_log = log_dir / f"{today}_errors.log"
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # File Handler
    file_handler = RotatingFileHandler(
        main_log,
        maxBytes=5*1024*1024,
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    file_handler.addFilter(ExcludedMessagesFilter())
    root_logger.addHandler(file_handler)
    
    # Error Handler
    error_handler = RotatingFileHandler(
        error_log,
        maxBytes=5*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d\n%(message)s\n',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    root_logger.addHandler(error_handler)
    
    # Console Handler (uses original stdout to avoid recursion if GuiLogger is active)
    console_handler = logging.StreamHandler(sys.__stdout__)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter('%(levelname)s | %(message)s'))
    console_handler.addFilter(ExcludedMessagesFilter())
    root_logger.addHandler(console_handler)
    
    # Silence libs
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('WDM').setLevel(logging.ERROR)
    
    logger = logging.getLogger("JARVIS")
    return logger


class GuiLogger(io.TextIOBase):
    """
    Redirect output to GUI terminal.
    Inherits from TextIOBase to mimic a real file object (fixes speedtest/tqdm errors).
    """
    
    def __init__(self, gui_handler):
        self.gui_handler = gui_handler

    @property
    def encoding(self):
        """Property to satisfy tools checking encoding without being writable"""
        return 'utf-8'

    def write(self, message):
        # --- FIX: Handle Byte input from Flask/Subprocesses ---
        if isinstance(message, bytes):
            try:
                msg = message.decode('utf-8')
            except:
                msg = str(message)
        else:
            msg = str(message)

        if msg.strip():
            try:
                # Don't show internal debug prints
                if not msg.startswith('[DEBUG]'):
                    # Clean up trailing newlines for the UI
                    clean_msg = msg.strip().replace('\r', '')
                    self.gui_handler.show_terminal_output(clean_msg, color="white")
            except:
                pass
        return len(message)
    
    def flush(self):
        pass

    def isatty(self):
        """Pretend to be a terminal so progress bars show up"""
        return True

    def fileno(self):
        """
        Delegate to the real stdout file descriptor.
        This fixes 'AttributeError: GuiLogger object has no attribute fileno'
        """
        try:
            return sys.__stdout__.fileno()
        except:
            return 1 # Standard stdout fd