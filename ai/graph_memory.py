"""
GraphRAG (Relational Memory) for JARVIS
Stores facts as Triples: Subject -> Relation -> Object
"""
import sqlite3
import os
import logging
from pathlib import Path
from config.settings import DATA_DIR

logger = logging.getLogger(__name__)

class GraphMemory:
    def __init__(self):
        self.db_path = Path(DATA_DIR) / "graph_memory.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_graph (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    object TEXT NOT NULL,
                    UNIQUE(subject, relation, object)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_subject ON knowledge_graph(subject)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_object ON knowledge_graph(object)")

    def add_relation(self, subject: str, relation: str, obj: str):
        """Called by JARVIS to remember new facts"""
        subject, relation, obj = subject.lower(), relation.lower(), obj.lower()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO knowledge_graph (subject, relation, object) VALUES (?, ?, ?)",
                    (subject, relation, obj)
                )
            logger.info(f"🧠 Graph Memory Learned: [{subject}] --({relation})--> [{obj}]")
            return True
        except Exception as e:
            logger.error(f"Graph memory error: {e}")
            return False

    def query_graph(self, entity: str) -> str:
        """Retrieves all known relationships for an entity"""
        entity = entity.lower()
        results =[]
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get what the entity does/is
                cursor = conn.execute("SELECT relation, object FROM knowledge_graph WHERE subject = ?", (entity,))
                for rel, obj in cursor.fetchall():
                    results.append(f"{entity} {rel} {obj}")
                
                # Get things related to the entity
                cursor = conn.execute("SELECT subject, relation FROM knowledge_graph WHERE object = ?", (entity,))
                for subj, rel in cursor.fetchall():
                    results.append(f"{subj} {rel} {entity}")
                    
            if not results:
                return ""
            return " | ".join(results)
        except Exception as e:
            return ""

    def get_all_context(self) -> str:
        """Dumps a fast summary of the graph for the LLM prompt"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT subject, relation, object FROM knowledge_graph ORDER BY id DESC LIMIT 50")
                facts = [f"[{s}] --({r})--> [{o}]" for s, r, o in cursor.fetchall()]
                return "\n".join(facts)
        except:
            return ""

# Global Instance
graph_db = GraphMemory()