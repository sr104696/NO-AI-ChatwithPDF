"""
Indexing module for Offline PDF Intelligence.

Builds BM25 and TF-IDF indexes over extracted text chunks.
No neural embeddings - purely deterministic, statistical methods.
"""

import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import bm25s
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class BM25Indexer:
    """
    BM25 indexer for full-text search.
    
    Uses the bm25s library for fast, deterministic BM25 scoring.
    No neural components, no embeddings.
    """
    
    def __init__(self):
        """Initialize the BM25 indexer."""
        self.bm25_model: Optional[bm25s.BM25] = None
        self.corpus: List[str] = []
        self.chunk_metadata: List[Dict[str, Any]] = []
        self._is_indexed = False
    
    def build_index(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Build a BM25 index from text chunks.
        
        Args:
            chunks: List of chunk dicts with 'text' key and metadata
        """
        # Extract texts and metadata
        self.corpus = [chunk['text'] for chunk in chunks]
        self.chunk_metadata = [
            {
                'pdf_path': chunk.get('pdf_path', ''),
                'page_number': chunk.get('page_number', 0),
                'chunk_index': chunk.get('chunk_index', 0),
                'section_heading': chunk.get('section_heading', '')
            }
            for chunk in chunks
        ]
        
        # Tokenize and index
        print(f"Building BM25 index for {len(self.corpus)} chunks...")
        tokenized_corpus = bm25s.tokenize(self.corpus, stopwords='en')
        
        self.bm25_model = bm25s.BM25()
        self.bm25_model.index(tokenized_corpus)
        
        self._is_indexed = True
        print(f"BM25 index built successfully.")
    
    def search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """
        Search the index for a query.
        
        Args:
            query: Search query string
            k: Number of results to return
            
        Returns:
            List of (chunk_index, score) tuples sorted by relevance
        """
        if not self._is_indexed:
            raise ValueError("Index not built yet")
        
        # Tokenize query
        tokenized_query = bm25s.tokenize([query], stopwords='en')
        
        # Search
        results, scores = self.bm25_model.retrieve(
            tokenized_query, 
            corpus=self.corpus, 
            k=min(k, len(self.corpus))
        )
        
        # Return indices and scores
        if len(results) > 0 and len(scores) > 0:
            return list(zip(results[0], scores[0]))
        return []
    
    def save_index(self, index_dir: str) -> None:
        """
        Save the index to disk for persistence.
        
        Args:
            index_dir: Directory to save the index
        """
        os.makedirs(index_dir, exist_ok=True)
        
        # Save BM25 model
        index_path = os.path.join(index_dir, "bm25_index.json")
        self.bm25_model.save(index_path)
        
        # Save corpus and metadata
        with open(os.path.join(index_dir, "corpus.pkl"), 'wb') as f:
            pickle.dump(self.corpus, f)
        
        with open(os.path.join(index_dir, "metadata.json"), 'w') as f:
            json.dump(self.chunk_metadata, f)
        
        print(f"Index saved to {index_dir}")
    
    def load_index(self, index_dir: str) -> bool:
        """
        Load an index from disk.
        
        Args:
            index_dir: Directory containing the saved index
            
        Returns:
            True if loaded successfully
        """
        try:
            index_path = os.path.join(index_dir, "bm25_index.json")
            
            # Load BM25 model
            self.bm25_model = bm25s.BM25.load(index_path, load_corpus=False)
            
            # Load corpus
            with open(os.path.join(index_dir, "corpus.pkl"), 'rb') as f:
                self.corpus = pickle.load(f)
            
            # Load metadata
            with open(os.path.join(index_dir, "metadata.json"), 'r') as f:
                self.chunk_metadata = json.load(f)
            
            self._is_indexed = True
            print(f"Index loaded from {index_dir}")
            return True
            
        except Exception as e:
            print(f"Failed to load index: {e}")
            return False
    
    @property
    def is_indexed(self) -> bool:
        """Check if the index has been built."""
        return self._is_indexed
    
    def get_chunk_info(self, chunk_idx: int) -> Dict[str, Any]:
        """Get metadata for a specific chunk."""
        # Convert numpy types to Python native types
        if hasattr(chunk_idx, 'item'):
            chunk_idx = int(chunk_idx.item())
        else:
            chunk_idx = int(chunk_idx)
        
        if 0 <= chunk_idx < len(self.chunk_metadata):
            return self.chunk_metadata[chunk_idx]
        return {}


class TFIDFIndexer:
    """
    TF-IDF indexer for document similarity.
    
    Uses scikit-learn's TfidfVectorizer for computing
    cosine similarity between documents/chunks.
    """
    
    def __init__(self, max_features: int = 10000, 
                 ngram_range: Tuple[int, int] = (1, 2)):
        """
        Initialize the TF-IDF indexer.
        
        Args:
            max_features: Maximum number of features in vocabulary
            ngram_range: Range of n-grams to consider
        """
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words='english',
            ngram_range=ngram_range,
            min_df=1,
            max_df=0.95
        )
        self.tfidf_matrix = None
        self.corpus: List[str] = []
        self._is_indexed = False
    
    def build_index(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Build a TF-IDF index from text chunks.
        
        Args:
            chunks: List of chunk dicts with 'text' key
        """
        self.corpus = [chunk['text'] for chunk in chunks]
        
        print(f"Building TF-IDF index for {len(self.corpus)} chunks...")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
        self._is_indexed = True
        print("TF-IDF index built successfully.")
    
    def find_similar(self, chunk_idx: int, 
                     k: int = 5) -> List[Tuple[int, float]]:
        """
        Find chunks similar to a given chunk.
        
        Args:
            chunk_idx: Index of the query chunk
            k: Number of similar chunks to return
            
        Returns:
            List of (chunk_index, similarity_score) tuples
        """
        if not self._is_indexed:
            raise ValueError("Index not built yet")
        
        # Get query vector
        query_vector = self.tfidf_matrix[chunk_idx]
        
        # Compute cosine similarities
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # Get top-k (excluding self)
        sim_indices = np.argsort(similarities)[::-1]
        results = []
        for idx in sim_indices:
            if idx != chunk_idx:
                results.append((int(idx), float(similarities[idx])))
            if len(results) >= k:
                break
        
        return results
    
    def search_by_text(self, query: str, 
                       k: int = 10) -> List[Tuple[int, float]]:
        """
        Search for chunks similar to a text query.
        
        Args:
            query: Query text
            k: Number of results to return
            
        Returns:
            List of (chunk_index, similarity_score) tuples
        """
        if not self._is_indexed:
            raise ValueError("Index not built yet")
        
        # Transform query
        query_vector = self.vectorizer.transform([query])
        
        # Compute similarities
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:k]
        return [(int(idx), float(similarities[idx])) 
                for idx in top_indices if similarities[idx] > 0]
    
    @property
    def is_indexed(self) -> bool:
        """Check if the index has been built."""
        return self._is_indexed
