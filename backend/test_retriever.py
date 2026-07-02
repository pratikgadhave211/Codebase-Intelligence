import os
from core.retrieval.retriever import retrieve_chunks

def check():
    try:
        chunks = retrieve_chunks(
            query="How does authentication work?",
            repo_name="match3-frontend",
            top_k=5,
            commit_hash=None,
        )
        print("Success, chunks:", len(chunks))
        if not chunks:
            print("Returned empty list!")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check()
