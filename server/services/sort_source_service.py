from typing import List, Dict
from sentence_transformers import SentenceTransformer



class SortSourceService:
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    
    def sort_sources(self, query:str, search_results: list[dict]):
       query_embedding = self.embedding_model.encode(query)
       # Calculate similarities between the query and each source
       
       for res in search_results:
           res_embedding = self.embedding_model.encode(res['content'])
           print(res_embedding)
           
           #why to use numpy here? because we want to calculate the cosine similarity between the query and each source.
           #cosine similarity is a measure of similarity between two non-zero vectors of an inner product  