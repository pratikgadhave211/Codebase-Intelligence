import os
import asyncio
from core.storage.repo_metadata import get_repo_metadata
from core.llm.architecture import generate_architecture

cached = get_repo_metadata("match3-frontend")
if cached:
    chunks = [] # Just pass empty to see if it generates anything from context
    summary, mermaid = generate_architecture(chunks, cached["architecture_context"])
    print("Summary:")
    print(summary)
    print("Mermaid:")
    print(mermaid)
else:
    print("No cached data for match3-frontend")
