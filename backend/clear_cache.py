import os
from qdrant_client import QdrantClient
from config import QDRANT_URL, QDRANT_API_KEY, QDRANT_METADATA_COLLECTION
import hashlib

_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
repo_name = "match3-frontend"
metadata_id = hashlib.md5(repo_name.encode()).hexdigest()

_client.delete(
    collection_name=QDRANT_METADATA_COLLECTION,
    points_selector=[metadata_id],
)
print("Deleted cached metadata for", repo_name)
