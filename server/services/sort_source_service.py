from typing import List, Dict
from sentence_transformers import SentenceTransformer
import numpy as np



class SortSourceService:
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    
    def sort_sources(self, query: str, search_results: list[dict]):
        try:
            if not search_results:
                return []

            # Filter valid docs
            valid_docs = [
                res for res in search_results
                if res.get('content') and isinstance(res.get('content'), str) and res.get('content').strip()
            ]
            if not valid_docs:
                return search_results

            # Batch encode query and contents with normalized embeddings for fast vector cosine similarity
            query_embedding = self.embedding_model.encode(query, normalize_embeddings=True)
            contents = [res['content'] for res in valid_docs]
            doc_embeddings = self.embedding_model.encode(contents, normalize_embeddings=True)

            # Cosine similarity between normalized vectors is simply the dot product
            similarities = np.dot(doc_embeddings, query_embedding)

            relevant_docs = []
            for doc, sim in zip(valid_docs, similarities):
                score = float(sim)
                doc['score'] = score
                if score > 0.3:
                    relevant_docs.append(doc)

            # Sort the relevant docs in descending order of similarity score
            sorted_results = sorted(relevant_docs, key=lambda x: x['score'], reverse=True)
            return sorted_results if sorted_results else search_results
        except Exception as e:
            print(f"Error in sort_sources: {e}")
            return search_results