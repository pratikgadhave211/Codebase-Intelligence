import os
from config import QDRANT_URL, QDRANT_API_KEY
from qdrant_client import QdrantClient

def check():
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)
    try:
        results = client.query(
            collection_name="match3-frontend",
            query_text="How does authentication work?",
            limit=5,
        )
        print("Success, found:", len(results))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check()
