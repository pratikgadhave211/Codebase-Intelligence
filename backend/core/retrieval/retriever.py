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


def retrieve_chunks(
    query: str,
    repo_name: str,
    top_k: int = DEFAULT_TOP_K,
    commit_hash: str | None = None,
    collection_name: str | None = None,
) -> list[dict]:
    """Embed a query and return the top-k most relevant chunks from Qdrant."""
    coll = collection_name or repo_name

    try:
        existing = [c.name for c in _qdrant.get_collections().collections]
        if coll not in existing:
            print(f"[retriever.py] Collection '{coll}' not found.")
            return []
    except Exception as e:
        print(f"[retriever.py] Cannot connect to Qdrant: {e}")
        return []

    query_filter = None
    if commit_hash:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="commit_hash",
                    match=MatchValue(value=commit_hash),
                )
            ]
        )

    try:
        # Embed query text using NVIDIA API (truncate to safe length)
        safe_query = query[:4000]
        dense_vec = _nvidia_embedder.embed_query(safe_query)

        # Fetch dense results
        dense_results = _qdrant.search(
            collection_name=coll,
            query_vector=dense_vec,
            query_filter=query_filter,
            limit=top_k, 
        )

        def normalize(results):
            if not results:
                return {}
            scores = [r.score for r in results]
            min_s, max_s = min(scores), max(scores)
            if min_s == max_s:
                return {r.id: 1.0 for r in results}
            return {r.id: (r.score - min_s) / (max_s - min_s) for r in results}

        norm_dense = normalize(dense_results)

        chunk_map = {}
        for r in dense_results:
            if r.id not in chunk_map:
                chunk_map[r.id] = dict(r.payload)

        scored_chunks = []
        for chunk_id, payload in chunk_map.items():
            d_score = norm_dense.get(chunk_id, 0.0)
            payload["score"] = round(d_score, 4)
            payload["dense_score"] = round(d_score, 4)
            scored_chunks.append(payload)

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        final_chunks = scored_chunks[:top_k]

        print(f"[retriever.py] Query: '{query[:50]}...' -> {len(final_chunks)} chunks retrieved from '{repo_name}'")
        return final_chunks

    except UnexpectedResponse as e:
        print(f"[retriever.py] Qdrant search error: {e}")
        return []
    except Exception as e:
        print(f"[retriever.py] Unexpected retrieval error: {e}")
        return []


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