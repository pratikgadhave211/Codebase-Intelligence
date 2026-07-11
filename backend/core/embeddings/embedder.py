"""
Code Embedder

Embeds code chunks using NVIDIA Cloud Embeddings and stores them in Qdrant. 
Supports full ingestion and incremental indexing using deterministic point IDs 
(MD5 hashes) for targeted upserts and deletions.
"""

import hashlib
import os
import shutil

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import PayloadSchemaType, VectorParams, Distance, PointStruct
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from config import QDRANT_URL, QDRANT_API_KEY, HF_TOKEN

_qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=60,
)

# Initialize Hugging Face Cloud Embeddings
_hf_embedder = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    huggingfacehub_api_token=HF_TOKEN,
)


def _chunk_id(
    repo_name: str,
    file_path: str,
    chunk_name: str,
    start_line: int,
    commit_hash: str | None = None,
) -> str:
    """
    Deterministic ID for a chunk — same input always produces the same ID.
    Uses MD5 hex digest (32 chars) — Qdrant accepts string IDs.
    """
    raw = f"{repo_name}:{file_path}:{chunk_name}:{start_line}:{commit_hash or 'HEAD'}"
    return hashlib.md5(raw.encode()).hexdigest()


def _build_ids_and_payloads(
    chunks: list[dict],
    repo_name: str,
    commit_hash: str | None = None,
) -> tuple[list[str], list[str], list[dict]]:
    """Build deterministic IDs and payloads for a list of chunks."""
    ids: list[str] = []
    payloads: list[dict] = []
    texts: list[str] = []

    for chunk in chunks:
        chunk_id = _chunk_id(
            repo_name,
            chunk["file_path"],
            chunk["name"],
            chunk["start_line"],
            commit_hash,
        )
        ids.append(chunk_id)
        texts.append(chunk["text"])
        payload = {
            "text":        chunk["text"],
            "file_path":   chunk["file_path"],
            "chunk_type":  chunk["chunk_type"],
            "name":        chunk["name"],
            "start_line":  chunk["start_line"],
            "end_line":    chunk["end_line"],
            "language":    chunk["language"],
            "repo_name":   repo_name,
        }
        if commit_hash:
            payload["commit_hash"] = commit_hash
        payloads.append(payload)

    return ids, texts, payloads


def _ensure_payload_index(collection_name: str) -> None:
    """Create keyword indexes on file_path and commit_hash."""
    for field in ("file_path", "commit_hash"):
        try:
            _qdrant.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass


def _delete_if_exists(collection_name: str) -> None:
    """Delete a collection if it exists."""
    try:
        existing = [c.name for c in _qdrant.get_collections().collections]
        if collection_name in existing:
            _qdrant.delete_collection(collection_name)
            print(f"[embedder.py] Deleted existing collection '{collection_name}'")
    except Exception as e:
        print(f"[embedder.py] Warning: could not check/delete collection: {e}")


def _batch_upsert(coll: str, ids: list[str], texts: list[str], payloads: list[dict]):
    """Helper to embed and upsert in batches to avoid API limits."""
    batch_size = 50
    chunks_stored = 0

    for i in range(0, len(texts), batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_texts = texts[i : i + batch_size]
        batch_payloads = payloads[i : i + batch_size]

        # Truncate strings to ~4000 chars to avoid massive HTTP payloads
        safe_texts = [t[:4000] for t in batch_texts]
        
        # Call Hugging Face API to embed
        embeddings = _hf_embedder.embed_documents(safe_texts)

        # Build Qdrant PointStructs
        points = [
            PointStruct(id=point_id, vector=vector, payload=payload)
            for point_id, vector, payload in zip(batch_ids, embeddings, batch_payloads)
        ]

        # Push to Qdrant
        _qdrant.upsert(
            collection_name=coll,
            points=points
        )
        chunks_stored += len(points)
        print(f"[embedder.py] Upserted batch of {len(points)} chunks... ({chunks_stored}/{len(texts)})")

    return chunks_stored


def embed_and_store(
    chunks: list[dict],
    repo_name: str,
    commit_hash: str | None = None,
    collection_name: str | None = None,
) -> dict:
    """Full index path — embed ALL chunks and store in a fresh Qdrant collection."""
    coll = collection_name or repo_name

    if not chunks:
        return {
            "status": "error",
            "message": "No chunks provided — nothing to embed.",
            "chunks_stored": 0,
        }

    # Recreate collection with Hugging Face dimension size (384)
    _delete_if_exists(coll)
    try:
        _qdrant.create_collection(
            collection_name=coll,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
    except Exception as e:
        print(f"[embedder.py] Warning creating collection: {e}")

    ids, texts, payloads = _build_ids_and_payloads(chunks, repo_name, commit_hash)

    try:
        print(f"[embedder.py] Requesting embeddings from NVIDIA API for {len(chunks)} chunks...")
        
        chunks_stored = _batch_upsert(coll, ids, texts, payloads)
        _ensure_payload_index(coll)

        print(f"[embedder.py] Stored {chunks_stored} chunks in '{coll}'")
        return {
            "status":        "success",
            "repo_name":     repo_name,
            "chunks_stored": chunks_stored,
        }
    except Exception as e:
        return {
            "status":  "error",
            "message": f"Embedding/storage failed: {str(e)}",
            "chunks_stored": 0,
        }


def upsert_chunks(
    chunks: list[dict],
    repo_name: str,
    commit_hash: str | None = None,
    collection_name: str | None = None,
) -> dict:
    """Incremental path — embed and upsert only the given chunks."""
    coll = collection_name or repo_name

    if not chunks:
        return {
            "status": "success",
            "repo_name": repo_name,
            "chunks_stored": 0,
        }

    ids, texts, payloads = _build_ids_and_payloads(chunks, repo_name, commit_hash)

    try:
        print(f"[embedder.py] Requesting NVIDIA embeddings for incremental upsert of {len(chunks)} chunks...")
        chunks_stored = _batch_upsert(coll, ids, texts, payloads)

        print(f"[embedder.py] Upserted {chunks_stored} chunks in '{coll}'")
        return {
            "status":        "success",
            "repo_name":     repo_name,
            "chunks_stored": chunks_stored,
        }
    except Exception as e:
        return {
            "status":  "error",
            "message": f"Upsert failed: {str(e)}",
            "chunks_stored": 0,
        }


def delete_file_chunks(repo_name: str, file_paths: list[str]) -> int:
    """Delete all Qdrant points belonging to the given file paths."""
    if not file_paths:
        return 0
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchAny
        _qdrant.delete(
            collection_name=repo_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="file_path",
                        match=MatchAny(any=file_paths),
                    )
                ]
            ),
        )
        print(f"[embedder.py] Deleted chunks for {len(file_paths)} files from '{repo_name}'")
        return len(file_paths)
    except Exception as e:
        print(f"[embedder.py] Failed to delete file chunks: {e}")
        return 0