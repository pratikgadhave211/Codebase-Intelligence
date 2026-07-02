import os
from config import QDRANT_URL, QDRANT_API_KEY
from qdrant_client import QdrantClient

def check():
    print(f"URL: {QDRANT_URL}")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)
    try:
        collections = client.get_collections()
        print("Collections:", [c.name for c in collections.collections])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check()
