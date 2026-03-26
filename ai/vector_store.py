"""
JARVIS Vector Memory (FAISS)
Loads user data and retrieves relevant context based on semantic similarity.
"""
import logging
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config.settings import DATA_DIR
import json
logger = logging.getLogger(__name__)

LEARNING_DATA_DIR = DATA_DIR / "learning_data"
LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)

import csv # Add this import at the top

class VectorMemory:
    def __init__(self):
        logger.info("🧠 Initializing Vector Memory...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        self.vector_store = None
        self.build_index()

    def load_learning_data(self):
        docs = []
        # 1. Load Text Files
        for file_path in LEARNING_DATA_DIR.glob("*.txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                docs.append(Document(page_content=f.read().strip(), metadata={"source": file_path.name}))
        
        # 2. LOAD CSV FILES (This is the game changer)
        for file_path in LEARNING_DATA_DIR.glob("*.csv"):
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert row to a natural language sentence
                    fact = f"The {row['Category']} {row['Entity']} is {row['Value']}. Details: {row['Context']}."
                    docs.append(Document(page_content=fact, metadata={"source": file_path.name}))
        return docs

    def build_index(self):
        docs = self.load_learning_data()
        if not docs:
            self.vector_store = FAISS.from_texts(["No personal data found."], self.embeddings)
        else:
            # Smaller chunks are better for CSV rows
            chunks = self.text_splitter.split_documents(docs)
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
            logger.info(f"✅ Vector Memory built with {len(chunks)} chunks.")

    # --- THE FULL CORRECTED FUNCTION ---
    def retrieve_context(self, query: str, k=6) -> str:
        if not self.vector_store:
            return ""
        
        # MMR (Maximal Marginal Relevance) 
        # fetch_k=20: Looks at 20 most similar chunks
        # k=6: Returns the 6 that are most DIVERSE (prevents returning 6 identical chunks)
        results = self.vector_store.max_marginal_relevance_search(
            query, 
            k=k, 
            fetch_k=20
        )
        
        context = "\n".join([f"- {doc.page_content}" for doc in results])
        return f"\n=== RELEVANT PERSONAL KNOWLEDGE ===\n{context}\n===================================\n"
# Global instance
memory = None

def init_memory():
    global memory
    if memory is None:
        memory = VectorMemory()

def get_memory():
    global memory
    return memory