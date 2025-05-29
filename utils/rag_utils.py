from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import faiss
import numpy as np
import os
import pickle

class RAGSystem:
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight model
        self.index_path = "utils/vector_store.faiss"
        self.metadata_path = "utils/metadata.pkl"
        
    def create_vector_store(self, documents):
        """Create FAISS index from documents"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            length_function=len
        )
        
        chunks = []
        metadatas = []
        for doc in documents:
            splits = text_splitter.split_text(doc["text"])
            for split in splits:
                chunks.append(split)
                metadatas.append(doc["metadata"])
        
        embeddings = self.embedding_model.encode(chunks, show_progress_bar=True)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        
        # Save index and metadata
        faiss.write_index(index, self.index_path)
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(metadatas, f)
    
    def load_vector_store(self):
        """Load existing FAISS index"""
        if not os.path.exists(self.index_path):
            raise FileNotFoundError("Vector store not found. Please create it first.")
        
        index = faiss.read_index(self.index_path)
        with open(self.metadata_path, 'rb') as f:
            metadatas = pickle.load(f)
        return index, metadatas
    
    def search(self, query, k=3, filters=None):
        """Search the vector store"""
        index, metadatas = self.load_vector_store()
        query_embedding = self.embedding_model.encode([query])
        distances, indices = index.search(query_embedding, k)
        
        results = []
        for idx in indices[0]:
            if idx >= 0:
                metadata = metadatas[idx]
                # Apply filters
                if filters:
                    match = all(metadata.get(k) == v for k, v in filters.items())
                    if not match:
                        continue
                results.append({
                    "text": metadatas[idx].get("text", ""),
                    "metadata": metadata,
                    "score": float(distances[0][idx])
                })
        return sorted(results, key=lambda x: x["score"])