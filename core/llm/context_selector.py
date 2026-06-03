from pathlib import Path


HIGH_PRIORITY_FILES = {
    "main.py",
    "app.py",
    "server.py",
    "index.ts",
    "index.js",
    "main.tsx",
    "app.tsx",
    "config.py",
}


NEGATIVE_FILES = {
    "eslint.config.js",
    "postcss.config.js",
    "tailwind.config.js",
}


def score_file(path: str) -> int:

    score = 0

    file_name = Path(path).name.lower()
    path_lower = path.lower()

    if file_name in HIGH_PRIORITY_FILES:
        score += 100

    ARCH_KEYWORDS = [
        "api",
        "route",
        "router",
        "service",
        "agent",
        "controller",
        "core",
        "storage",
        "database",
        "db",
        "graph",
        "llm",
        "retrieval",
        "frontend",
        "backend",
    ]

    for keyword in ARCH_KEYWORDS:
        if keyword in path_lower:
            score += 20

    if "config" in file_name:
        score += 15

    if file_name in NEGATIVE_FILES:
        score -= 100

    return score


def select_architecture_chunks(chunks: list[dict], max_chunks: int = 12,) -> list[dict]:

    best_per_file = {}

    for chunk in chunks:

        path = chunk["file_path"]

        current = best_per_file.get(path)

        if current is None:
            best_per_file[path] = chunk

        elif len(chunk["text"]) > len(current["text"]):
            best_per_file[path] = chunk

    files = list(best_per_file.values())

    files.sort(
        key=lambda c: score_file(
            c["file_path"]
        ),
        reverse=True,
    )

    return files[:max_chunks]