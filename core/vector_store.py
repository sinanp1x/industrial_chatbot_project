import os
import faiss
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

class LocalVectorStore:
    def __init__(self, storage_dir: str = "./storage/faiss_index"):
        self.storage_dir = storage_dir
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.index_name = "roboai_index"
        self.store = None
        
        # Ensure storage directory exists
        os.makedirs(self.storage_dir, exist_ok=True)
        self.load_index()

    def _create_empty_store(self):
        # Create an empty FAISS index (MiniLM uses 384 dimensions)
        index = faiss.IndexFlatL2(384)
        return FAISS(
            embedding_function=self.embeddings,
            index=index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={},
        )

    def load_index(self):
        """Loads FAISS index from disk if it exists, otherwise creates empty."""
        index_path = os.path.join(self.storage_dir, f"{self.index_name}.faiss")
        if os.path.exists(index_path):
            try:
                self.store = FAISS.load_local(
                    self.storage_dir, 
                    self.embeddings, 
                    index_name=self.index_name,
                    allow_dangerous_deserialization=True # required for loading pickle docstore
                )
            except Exception as e:
                print(f"Error loading index, creating empty: {e}")
                self.store = self._create_empty_store()
        else:
            self.store = self._create_empty_store()

    def add_documents(self, documents: List[Document]):
        """Adds documents to the index and saves to disk."""
        if not documents:
            return
        
        if self.store is None:
            self.store = self._create_empty_store()
            
        self.store.add_documents(documents)
        self.save_index()

    def save_index(self):
        """Saves current index to disk."""
        if self.store:
            self.store.save_local(self.storage_dir, index_name=self.index_name)

    def search(self, query: str, k: int = 4) -> List[Document]:
        """Searches for similar chunks."""
        if not self.store:
            return []
        
        try:
            return self.store.similarity_search(query, k=k)
        except Exception:
            return []

    def clear(self):
        """Clears the current index."""
        self.store = self._create_empty_store()
        
        # Delete from disk
        index_path = os.path.join(self.storage_dir, f"{self.index_name}.faiss")
        pkl_path = os.path.join(self.storage_dir, f"{self.index_name}.pkl")
        
        if os.path.exists(index_path):
            os.remove(index_path)
        if os.path.exists(pkl_path):
            os.remove(pkl_path)
