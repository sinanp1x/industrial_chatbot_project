import tempfile
import os
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentLoader:
    def __init__(self):
        # Industrial manuals need safety warnings and steps to overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=850,
            chunk_overlap=150,
            separators=["\n\n### ", "\n\n## ", "\n\nDANGER:", "\n\nWARNING:", "\n\n", "\n", " "]
        )

    def load_and_split(self, uploaded_files) -> List[Document]:
        """
        Loads Streamlit uploaded files (PDF/TXT), parses them, and splits into semantic chunks.
        """
        documents = []
        for file in uploaded_files:
            # We need to save the uploaded file temporarily because loaders require a path
            suffix = os.path.splitext(file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(file.getvalue())
                temp_path = temp_file.name

            try:
                if suffix.lower() == ".pdf":
                    loader = PyPDFLoader(temp_path)
                    docs = loader.load()
                elif suffix.lower() == ".txt":
                    loader = TextLoader(temp_path, encoding='utf-8')
                    docs = loader.load()
                else:
                    continue # Unsupported format

                # Add metadata
                for doc in docs:
                    doc.metadata["source_file"] = file.name
                    doc.metadata["doc_type"] = "manual"

                documents.extend(docs)
            finally:
                os.remove(temp_path)

        # Split all documents
        chunks = self.text_splitter.split_documents(documents)
        
        # Add chunk id metadata
        for i, chunk in enumerate(chunks):
            file_name = chunk.metadata.get("source_file", "unknown")
            page_num = chunk.metadata.get("page", 0)
            chunk.metadata["chunk_id"] = f"{file_name}_p{page_num}_c{i}"
            
        return chunks
