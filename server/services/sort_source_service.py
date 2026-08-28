from typing import List, Dict
from sentence_transformers import SentenceTransformer
import numpy as np



class SortSourceService:
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    
    def sort_sources(self, query: str, search_results: list[dict]):
        try:
            relevant_docs = []
            query_embedding = self.embedding_model.encode(query)
            # Calculate similarities between the query and each source

            for res in search_results:
                content = res.get('content')
                if not content or not isinstance(content, str) or not content.strip():
                    continue

                res_embedding = self.embedding_model.encode(content)

                # np.linalg.norm is used to calculate the norm of a vector. The norm of a vector is a measure of its length or magnitude.
                # In this case, we are calculating the norm of the query embedding and the source embedding to normalize the dot product and obtain the cosine similarity.
                # why to use numpy here? because we want to calculate the cosine similarity between the query and each source.
                # cosine similarity is a measure of similarity between two non-zero vectors of an inner product
                similarity = float(
                    np.dot(query_embedding, res_embedding)
                    / (np.linalg.norm(query_embedding) * np.linalg.norm(res_embedding) + 1e-10)
                )

                res['score'] = similarity
                if similarity > 0.3:
                    relevant_docs.append(res)
                    # If the similarity score is greater than 0.3, we consider the source relevant and add it to the relevant_docs list.

            # Sort the relevant docs in descending order of similarity score
            sorted_results = sorted(relevant_docs, key=lambda x: x['score'], reverse=True)
            #what is lambda x: x['score']? It is a function that takes an input x and returns the value of the 'score' key in the dictionary x. In this case, it is used as the key for sorting the relevant_docs list in descending order of similarity score.
            # If no relevant docs are found, return the original search results
            return sorted_results if sorted_results else search_results
        except Exception as e:
            print(f"Error in sort_sources: {e}")
            return search_results  