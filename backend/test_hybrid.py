from core.embeddings.embedder import embed_and_store
from core.retrieval.retriever import retrieve_chunks

repo = "test_hybrid"
chunks = [
    {
        "text": "Authentication handles user login and sessions",
        "file_path": "src/auth.py",
        "chunk_type": "function",
        "name": "login",
        "start_line": 1,
        "end_line": 5,
        "language": "python"
    },
    {
        "text": "Database config and connection pooling",
        "file_path": "src/db.py",
        "chunk_type": "function",
        "name": "connect",
        "start_line": 1,
        "end_line": 5,
        "language": "python"
    }
]

print("Ingesting test chunks...")
res = embed_and_store(chunks, repo)
print("Ingest result:", res)

print("\nRetrieving chunks for 'user login'...")
results = retrieve_chunks("user login", repo, top_k=2)
for r in results:
    print(f"File: {r['file_path']} | Final Score: {r.get('score')} (Dense: {r.get('dense_score')}, Sparse: {r.get('sparse_score')})")
