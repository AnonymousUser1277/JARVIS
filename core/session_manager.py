import json
import os
import uuid
import time
from config.settings import DATA_DIR

CHAT_HISTORY_DIR = os.path.join(DATA_DIR, "chat_sessions")
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

class SessionManager:
    def __init__(self):
        self.session_id = str(uuid.uuid4())[:8]
        self.current_history = []

    def add_message(self, role, content):
        # Clean Python code out of the memory so it's just text
        if role == "assistant":
            if 'print("' in content:
                import re
                matches = re.findall(r'print\("([^"]*)"\)', content)
                if matches:
                    content = " ".join(matches)
        
        # --- NEW: Group sequential system messages together ---
        if role == "system" and self.current_history and self.current_history[-1]["role"] == "system":
            # Avoid appending exact duplicates
            if content not in self.current_history[-1]["content"]:
                self.current_history[-1]["content"] += f"\n{content}"
        else:
            self.current_history.append({"role": role, "content": content})
            
        self.save_session()

    def get_short_term_context(self, limit=10):
        """Returns last N messages for the prompt."""
        context = ""
        for msg in self.current_history[-limit:]:
            if msg['role'] == "user":
                role = "User"
            elif msg['role'] == "system":
                role = "System (Code Result)"
            else:
                role = "Jarvis"
            context += f"{role}: {msg['content']}\n"
        return context

    def save_session(self):
        """Saves current session to JSON."""
        file_path = os.path.join(CHAT_HISTORY_DIR, f"session_{self.session_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.current_history, f, indent=2)

# Global instance
session_mgr = SessionManager()