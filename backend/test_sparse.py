from qdrant_client import QdrantClient
from config import QDRANT_URL, QDRANT_API_KEY
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

demo = client.get_collection("test_hybrid")
print("Collection config:", demo.config.params.vectors)
print("Collection sparse config:", demo.config.params.sparse_vectors)
