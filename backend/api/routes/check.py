"""
api/routes/check.py — Check if a repo is already indexed in Qdrant.

GET /api/v1/check?repo_name=flask-boilerplate
Returns: {
    "indexed": true,
    "chunks": 37,
    "commit_sha": "abc123...",
    "needs_update": true
}

Enhanced for incremental indexing:
  - Returns the stored commit_sha so the frontend knows what version is indexed.
  - Compares against the current HEAD commit on GitHub.
  - Sets needs_update=true if the stored SHA differs from HEAD.
  - Frontend can show "Update available" instead of just hiding the ingest button.
"""

from fastapi import APIRouter
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from config import QDRANT_URL, QDRANT_API_KEY

from core.ingestion.cloner import extract_owner_repo, fetch_head_commit
from core.storage.repo_metadata import get_repo_metadata

router = APIRouter()

_qdrant: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return _qdrant


@router.get("/check")
def check_repo(repo_name: str, github_url: str | None = None):
    """
    Return whether a repo_name collection exists, its chunk count,
    and whether an update is available.

    If github_url is provided, also checks the current HEAD commit
    against the stored commit SHA to determine if re-indexing is needed.
    """
    try:
        info = get_client().get_collection(repo_name)
        count = info.points_count or 0
        indexed = count > 0
    except (UnexpectedResponse, Exception):
        return {
            "indexed": False,
            "chunks": 0,
            "commit_sha": None,
            "needs_update": False,
        }

    if not indexed:
        return {
            "indexed": False,
            "chunks": 0,
            "commit_sha": None,
            "needs_update": False,
        }

    # Fetch stored commit SHA from metadata
    stored_sha = None
    metadata = get_repo_metadata(repo_name)
    if metadata:
        stored_sha = metadata.get("commit_sha")

    # If github_url provided, compare against current HEAD
    needs_update = False
    if github_url and stored_sha:
        try:
            owner, repo = extract_owner_repo(github_url)
            current_sha = fetch_head_commit(owner, repo)
            if current_sha and current_sha != stored_sha:
                needs_update = True
        except Exception:
            pass  # Can't determine — don't flag as needing update

    return {
        "indexed": True,
        "chunks": count,
        "commit_sha": stored_sha,
        "needs_update": needs_update,
    }