"""
Code Retriever

Handles semantic search over indexed code chunks in Qdrant. Embeds queries
using the same dense and sparse models used during ingestion, and retrieves
the top-k most relevant chunks using hybrid search.
"""

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from config import QDRANT_URL, QDRANT_API_KEY
from fastembed import TextEmbedding, SparseTextEmbedding

# Use the same models as embedder.py
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL = "Qdrant/bm25"

# Initialize FastEmbed directly so we can generate vectors manually
# without relying on QdrantClient's auto-magic which is limited in v1.9.1
_dense_model = TextEmbedding(EMBEDDING_MODEL)
_sparse_model = SparseTextEmbedding(SPARSE_MODEL)

_qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=60,
)

# Default number of chunks to retrieve per query.
# 5 chunks × ~750 tokens each = ~3750 tokens of context.
# Well within Groq's 6000 TPM limit per request.
DEFAULT_TOP_K = 5


def retrieve_chunks(
    query: str,
    repo_name: str,
    top_k: int = DEFAULT_TOP_K,
    commit_hash: str | None = None,
    collection_name: str | None = None,
) -> list[dict]:
    """
    Embed a query and return the top-k most relevant chunks from Qdrant.

    Args:
        query           : Natural language question or search term
        repo_name       : Qdrant collection to search in (= repo name from cloner)
        top_k           : Number of chunks to return
        commit_hash     : If provided, filter results to only this commit's chunks
        collection_name : Override collection name (for versioned collections)

    Returns:
        List of chunk dicts, each containing:
        {
            "text":       "def authenticate(user, pwd): ...",
            "file_path":  "src/auth.py",
            "chunk_type": "function",
            "name":       "authenticate",
            "start_line": 14,
            "end_line":   38,
            "language":   "python",
            "score":      0.87,   ← cosine similarity (0.0 to 1.0)
        }
        Returns empty list on any error — never raises.
    """
    coll = collection_name or repo_name

    # First check the collection exists
    try:
        existing = [c.name for c in _qdrant.get_collections().collections]
        if coll not in existing:
            print(
                f"[retriever.py] Collection '{coll}' not found. "
                f"Has this repo been ingested yet?"
            )
            return []
    except Exception as e:
        print(f"[retriever.py] Cannot connect to Qdrant: {e}")
        return []

    # Build optional filter for commit_hash
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

    # Perform semantic search
    try:
        # Embed query text
        dense_vec = list(_dense_model.embed([query]))[0]
        sparse_vec = list(_sparse_model.embed([query]))[0]

        # 1. Fetch dense results
        dense_results = _qdrant.search(
            collection_name=coll,
            query_vector=("fast-bge-small-en", dense_vec.tolist()),
            query_filter=query_filter,
            limit=top_k * 2,  # Fetch more for fusion
        )

        # 2. Fetch sparse results (BM25)
        # Catch errors here if the user hasn't re-ingested their repo yet
        sparse_results = []
        try:
            sparse_results = _qdrant.search(
                collection_name=coll,
                query_vector=models.NamedSparseVector(
                    name="fast-sparse-bm25",
                    vector=models.SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist()
                    )
                ),
                query_filter=query_filter,
                limit=top_k * 2,
            )
        except UnexpectedResponse as e:
            if "not found" in str(e) or "doesn't exist" in str(e):
                print(f"[retriever.py] Warning: Sparse vector 'fast-sparse-bm25' not found. Did you re-ingest the repo?")
            else:
                print(f"[retriever.py] Qdrant sparse search error: {e}")

        # 3. Min-Max Normalization helper
        def normalize(results):
            if not results:
                return {}
            scores = [r.score for r in results]
            min_s, max_s = min(scores), max(scores)
            if min_s == max_s:
                return {r.id: 1.0 for r in results}
            return {r.id: (r.score - min_s) / (max_s - min_s) for r in results}

        norm_dense = normalize(dense_results)
        norm_sparse = normalize(sparse_results)

        # Map IDs back to full chunk payloads
        # Using dicts for O(1) lookups
        chunk_map = {}
        for r in dense_results + sparse_results:
            if r.id not in chunk_map:
                chunk_map[r.id] = dict(r.payload)

        # 4. Score Fusion: 0.7 Dense + 0.3 Sparse
        scored_chunks = []
        for chunk_id, payload in chunk_map.items():
            d_score = norm_dense.get(chunk_id, 0.0)
            s_score = norm_sparse.get(chunk_id, 0.0)
            final_score = (0.7 * d_score) + (0.3 * s_score)
            
            payload["score"] = round(final_score, 4)
            payload["dense_score"] = round(d_score, 4)
            payload["sparse_score"] = round(s_score, 4)
            scored_chunks.append(payload)

        # Sort descending by final score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        final_chunks = scored_chunks[:top_k]

        print(
            f"[retriever.py] Hybrid Query: '{query[:50]}...' -> "
            f"{len(final_chunks)} chunks retrieved from '{repo_name}'"
        )
        return final_chunks

    except UnexpectedResponse as e:
        print(f"[retriever.py] Qdrant search error: {e}")
        return []
    except Exception as e:
        print(f"[retriever.py] Unexpected retrieval error: {e}")
        import traceback
        traceback.print_exc()
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