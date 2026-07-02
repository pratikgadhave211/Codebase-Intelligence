"""
tests/test_embedder.py — Unit tests for embedder.py deterministic ID generation.

Tests that _chunk_id() produces stable, deterministic IDs and that
different inputs produce different IDs.
"""

from core.embeddings.embedder import _chunk_id


class TestChunkId:
    """Tests for _chunk_id() deterministic ID generation."""

    def test_deterministic(self):
        """Same input always produces the same ID."""
        id1 = _chunk_id("myrepo", "src/auth.py", "authenticate", 14)
        id2 = _chunk_id("myrepo", "src/auth.py", "authenticate", 14)
        assert id1 == id2

    def test_different_repo(self):
        """Different repo_name → different ID."""
        id1 = _chunk_id("repo_a", "src/auth.py", "authenticate", 14)
        id2 = _chunk_id("repo_b", "src/auth.py", "authenticate", 14)
        assert id1 != id2

    def test_different_file(self):
        """Different file_path → different ID."""
        id1 = _chunk_id("myrepo", "src/auth.py", "authenticate", 14)
        id2 = _chunk_id("myrepo", "src/users.py", "authenticate", 14)
        assert id1 != id2

    def test_different_name(self):
        """Different chunk_name → different ID."""
        id1 = _chunk_id("myrepo", "src/auth.py", "authenticate", 14)
        id2 = _chunk_id("myrepo", "src/auth.py", "authorize", 14)
        assert id1 != id2

    def test_different_line(self):
        """Different start_line → different ID."""
        id1 = _chunk_id("myrepo", "src/auth.py", "authenticate", 14)
        id2 = _chunk_id("myrepo", "src/auth.py", "authenticate", 50)
        assert id1 != id2

    def test_returns_hex_string(self):
        """ID should be a 32-character hex string (MD5 digest)."""
        chunk_id = _chunk_id("myrepo", "src/auth.py", "func", 1)
        assert isinstance(chunk_id, str)
        assert len(chunk_id) == 32
        # Verify it's valid hex
        int(chunk_id, 16)

    def test_no_collisions_across_similar_inputs(self):
        """Closely related inputs should not collide."""
        ids = set()
        for i in range(100):
            ids.add(_chunk_id("repo", "file.py", f"func_{i}", i))
        assert len(ids) == 100
