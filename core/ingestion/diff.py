"""
core/ingestion/diff.py — Computes file-level diffs for incremental indexing.

Pure function, no side effects, no I/O. Compares the current file list
(from walker.py) against previously stored file hashes (from repo_metadata)
to classify each file as added, modified, deleted, or unchanged.

This is the decision-maker for incremental indexing:
  - added + modified files → re-chunk and re-embed
  - deleted files → remove stale chunks from Qdrant
  - unchanged files → skip entirely (saves time and API quota)
"""


def compute_file_diff(
    current_files: list[dict],
    stored_hashes: dict[str, str],
) -> dict:
    """
    Compare current file list against stored file hashes.

    Args:
        current_files: List of file info dicts from walker.py.
                       Each dict must have "rel_path" and "content_hash" keys.
        stored_hashes: Dict of {rel_path: content_hash} from repo_metadata.
                       Empty dict on first index (no previous data).

    Returns:
        {
            "added":     [file_info, ...],   # new files not in stored_hashes
            "modified":  [file_info, ...],   # files whose content hash changed
            "deleted":   ["rel_path", ...],  # paths in stored but not in current
            "unchanged": [file_info, ...],   # same hash — skip these
        }
    """
    current_map = {f["rel_path"]: f for f in current_files}
    current_paths = set(current_map.keys())
    stored_paths = set(stored_hashes.keys())

    added = [current_map[p] for p in sorted(current_paths - stored_paths)]
    deleted = sorted(stored_paths - current_paths)

    modified = []
    unchanged = []
    for p in sorted(current_paths & stored_paths):
        if current_map[p]["content_hash"] != stored_hashes[p]:
            modified.append(current_map[p])
        else:
            unchanged.append(current_map[p])

    return {
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "unchanged": unchanged,
    }
