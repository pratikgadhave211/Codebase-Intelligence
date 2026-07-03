"""
Code Retriever

Handles semantic search over indexed code chunks in Qdrant. Embeds queries
using the NVIDIA Cloud Embeddings API and retrieves the top-k most relevant chunks.
"""

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from config import QDRANT_URL, QDRANT_API_KEY, NVIDIA_API_KEY

_qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=60,
)

# Initialize NVIDIA Cloud Embeddings
_nvidia_embedder = NVIDIAEmbeddings(
    model="nvidia/nv-embedqa-e5-v5",
    nvidia_api_key=NVIDIA_API_KEY,
    truncate="END"
)

DEFAULT_TOP_K = 5


from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from pydantic import Field
from typing import List, Any 

class DenseQdrantRetriever(BaseRetriever):
    repo_name: str
    commit_hash: str | None = None
    top_k: int = 5
    collection_name: str | None = None

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        coll = self.collection_name or self.repo_name
        try:
            existing = [c.name for c in _qdrant.get_collections().collections]
            if coll not in existing:
                return []
        except Exception:
            return []

        query_filter = None
        if self.commit_hash:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="commit_hash",
                        match=MatchValue(value=self.commit_hash),
                    )
                ]
            )

        try:
            safe_query = query[:4000]
            dense_vec = _nvidia_embedder.embed_query(safe_query)
            dense_results = _qdrant.query_points(
                collection_name=coll,
                query=dense_vec,
                query_filter=query_filter,
                limit=self.top_k,
                with_payload=True,
            ).points

            docs = []
            for r in dense_results:
                payload = dict(r.payload)
                payload["score"] = round(r.score, 4)
                payload["dense_score"] = round(r.score, 4)
                docs.append(Document(page_content=payload.get("text", ""), metadata=payload))
            
            return docs
        except Exception:
            return []

def retrieve_chunks(
    query: str,
    repo_name: str,
    top_k: int = DEFAULT_TOP_K,
    commit_hash: str | None = None,
    collection_name: str | None = None,
) -> list[dict]:
    """Embed a query and return the top-k most relevant chunks using EnsembleRetriever."""
    coll = collection_name or repo_name

    # 1. Initialize Dense Retriever
    dense_retriever = DenseQdrantRetriever(
        repo_name=repo_name,
        commit_hash=commit_hash,
        top_k=top_k,
        collection_name=collection_name
    )

    # 2. Initialize BM25 Retriever
    # Fetch all chunks to build the BM25 index
    all_chunks = retrieve_all_chunks(coll, limit=100000)
    if not all_chunks:
        return []

    docs_for_bm25 = [Document(page_content=c.get("text", ""), metadata=c) for c in all_chunks]
    
    # Check if we have documents to avoid bm25 failure
    if not docs_for_bm25:
        return []
        
    bm25_retriever = BM25Retriever.from_documents(docs_for_bm25)
    bm25_retriever.k = top_k

    # 3. Retrieve individually
    bm25_docs = bm25_retriever.invoke(query)
    dense_docs = dense_retriever.invoke(query)
    
    # 4. Combine using Reciprocal Rank Fusion (RRF)
    rrf_k = 60
    scores = {}
    docs_map = {}
    
    # helper to get unique id
    def get_id(doc):
        # Fallback to hash of page_content if no id in metadata
        return str(doc.metadata.get("id", hash(doc.page_content)))

    for i, doc in enumerate(bm25_docs):
        doc_id = get_id(doc)
        # weight 0.5 for bm25
        scores[doc_id] = scores.get(doc_id, 0) + 0.5 * (1 / (rrf_k + i))
        docs_map[doc_id] = doc.metadata
        
    for i, doc in enumerate(dense_docs):
        doc_id = get_id(doc)
        # weight 0.5 for dense
        scores[doc_id] = scores.get(doc_id, 0) + 0.5 * (1 / (rrf_k + i))
        docs_map[doc_id] = doc.metadata
        
    # Sort by RRF score
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # 5. Extract metadata (payloads) and return up to top_k
    final_chunks = []
    for doc_id, score in sorted_docs[:top_k]:
        payload = docs_map[doc_id]
        payload["hybrid_score"] = round(score, 6)
        final_chunks.append(payload)

    print(f"[retriever.py] Query: '{query[:50]}...' -> {len(final_chunks)} chunks retrieved using Hybrid Search")
    return final_chunks


def retrieve_all_chunks(repo_name: str, limit: int = 50) -> list[dict]:
    """
    Retrieve up to `limit` chunks from a collection without a query.
    Used for architecture analysis and bug detection — where we want
    a broad sample of the codebase rather than query-specific results.

    Qdrant's scroll() method pages through all points in a collection.
    We use it here to get a representative sample of the codebase.
    """
    try:
        # scroll() returns (list_of_records, next_page_offset)
        # We only need the first page for our use case
        records, _ = _qdrant.scroll(
            collection_name=repo_name,
            limit=limit,
            with_payload=True,
            with_vectors=False,  # Don't return vectors — saves bandwidth
        )

        chunks = []
        for record in records:
            chunk = dict(record.payload)
            chunk["score"] = 1.0  # No relevance score for scroll — set to 1.0
            chunks.append(chunk)

        print(
            f"[retriever.py] Scrolled {len(chunks)} chunks from '{repo_name}'"
        )
        return chunks

    except Exception as e:
        print(f"[retriever.py] Scroll error for '{repo_name}': {e}")
        return []