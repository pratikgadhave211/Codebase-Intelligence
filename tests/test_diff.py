"""
tests/test_diff.py — Unit tests for core/ingestion/diff.py

Tests the compute_file_diff() function with all four change categories:
added, modified, deleted, unchanged.
"""

from core.ingestion.diff import compute_file_diff


def _make_file(rel_path: str, content_hash: str) -> dict:
    """Helper to create a file info dict matching walker.py output format."""
    return {
        "path": f"/tmp/repo/{rel_path}",
        "rel_path": rel_path,
        "language": "python",
        "size": 1024,
        "content_hash": content_hash,
    }


class TestComputeFileDiff:
    """Tests for compute_file_diff()."""

    def test_all_added_when_no_stored_hashes(self):
        """First-time index: everything is 'added', nothing else."""
        current = [
            _make_file("src/main.py", "aaa"),
            _make_file("src/utils.py", "bbb"),
        ]
        stored = {}

        result = compute_file_diff(current, stored)

        assert len(result["added"]) == 2
        assert len(result["modified"]) == 0
        assert len(result["deleted"]) == 0
        assert len(result["unchanged"]) == 0

    def test_all_unchanged(self):
        """Re-index with no changes: everything is 'unchanged'."""
        current = [
            _make_file("src/main.py", "aaa"),
            _make_file("src/utils.py", "bbb"),
        ]
        stored = {"src/main.py": "aaa", "src/utils.py": "bbb"}

        result = compute_file_diff(current, stored)

        assert len(result["added"]) == 0
        assert len(result["modified"]) == 0
        assert len(result["deleted"]) == 0
        assert len(result["unchanged"]) == 2

    def test_modified_file(self):
        """One file changed its hash → classified as 'modified'."""
        current = [
            _make_file("src/main.py", "aaa_v2"),  # hash changed
            _make_file("src/utils.py", "bbb"),     # same
        ]
        stored = {"src/main.py": "aaa", "src/utils.py": "bbb"}

        result = compute_file_diff(current, stored)

        assert len(result["modified"]) == 1
        assert result["modified"][0]["rel_path"] == "src/main.py"
        assert len(result["unchanged"]) == 1
        assert result["unchanged"][0]["rel_path"] == "src/utils.py"

    def test_deleted_file(self):
        """A file in stored but not in current → classified as 'deleted'."""
        current = [
            _make_file("src/main.py", "aaa"),
        ]
        stored = {"src/main.py": "aaa", "src/old_module.py": "ccc"}

        result = compute_file_diff(current, stored)

        assert len(result["deleted"]) == 1
        assert "src/old_module.py" in result["deleted"]
        assert len(result["unchanged"]) == 1

    def test_added_file(self):
        """A file in current but not in stored → classified as 'added'."""
        current = [
            _make_file("src/main.py", "aaa"),
            _make_file("src/new_feature.py", "ddd"),
        ]
        stored = {"src/main.py": "aaa"}

        result = compute_file_diff(current, stored)

        assert len(result["added"]) == 1
        assert result["added"][0]["rel_path"] == "src/new_feature.py"
        assert len(result["unchanged"]) == 1

    def test_mixed_changes(self):
        """All four categories at once."""
        current = [
            _make_file("src/main.py", "aaa"),         # unchanged
            _make_file("src/utils.py", "bbb_v2"),     # modified
            _make_file("src/new.py", "eee"),           # added
        ]
        stored = {
            "src/main.py": "aaa",
            "src/utils.py": "bbb",
            "src/deleted.py": "ddd",
        }

        result = compute_file_diff(current, stored)

        assert len(result["added"]) == 1
        assert result["added"][0]["rel_path"] == "src/new.py"

        assert len(result["modified"]) == 1
        assert result["modified"][0]["rel_path"] == "src/utils.py"

        assert len(result["deleted"]) == 1
        assert "src/deleted.py" in result["deleted"]

        assert len(result["unchanged"]) == 1
        assert result["unchanged"][0]["rel_path"] == "src/main.py"

    def test_empty_current_and_stored(self):
        """Edge case: both inputs empty."""
        result = compute_file_diff([], {})

        assert result["added"] == []
        assert result["modified"] == []
        assert result["deleted"] == []
        assert result["unchanged"] == []

    def test_all_deleted(self):
        """Edge case: current is empty but stored has files."""
        stored = {"src/a.py": "aaa", "src/b.py": "bbb"}

        result = compute_file_diff([], stored)

        assert len(result["deleted"]) == 2
        assert len(result["added"]) == 0
        assert len(result["modified"]) == 0
        assert len(result["unchanged"]) == 0
