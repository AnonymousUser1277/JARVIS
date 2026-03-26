import os
import sqlite3
import threading
import time
from pathlib import Path
from config.settings import DATA_DIR

class LocalFileIndexer:
    def __init__(self):
        self.db_path = Path(DATA_DIR) / "file_index.db"
        self._init_db()
        # Scan Documents, Downloads, and Desktop
        self.scan_dirs =[
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop")
        ]
        # Start background indexing
        threading.Thread(target=self._scan_loop, daemon=True).start()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    filename TEXT,
                    filepath TEXT PRIMARY KEY,
                    extension TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_filename ON files(filename)")

    def _scan_loop(self):
        """Scans folders every 30 minutes in the background"""
        while True:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    for directory in self.scan_dirs:
                        for root, _, files in os.walk(directory):
                            for file in files:
                                filepath = os.path.join(root, file)
                                ext = os.path.splitext(file)[1].lower()
                                conn.execute(
                                    "INSERT OR REPLACE INTO files (filename, filepath, extension) VALUES (?, ?, ?)",
                                    (file.lower(), filepath, ext)
                                )
                time.sleep(1800) # Sleep 30 mins
            except Exception as e:
                time.sleep(60)

    def search(self, keyword: str):
        """Allows JARVIS to instantly find files"""
        keyword = f"%{keyword.lower()}%"
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT filepath FROM files WHERE filename LIKE ? LIMIT 5", (keyword,))
                results = [row[0] for row in cursor.fetchall()]
                return results if results else ["File not found."]
        except:
            return["Database error."]

file_indexer = LocalFileIndexer()