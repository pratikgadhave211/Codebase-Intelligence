"""
Configuration Module

Single source of truth for all environment variables. Loads variables from the .env file
and exposes them as strongly typed Python constants. Validates required variables at startup.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file

load_dotenv()


# -----------------------------------------------------------------------
# GEMINI_API_KEY
# Used by: core/embeddings/embedder.py, core/llm/client.py
# Get it free at: aistudio.google.com → Get API Key
# -----------------------------------------------------------------------
NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
HF_TOKEN: str = os.getenv("HF_TOKEN", "")

# -----------------------------------------------------------------------
# GITHUB_TOKEN (optional)
# Authenticates GitHub API requests to raise rate limit from 60 to 5,000/hr.
# Get one at: github.com → Settings → Developer settings → Personal access tokens
# Only needed if you re-index repos frequently.
# -----------------------------------------------------------------------
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

# -----------------------------------------------------------------------
# QDRANT_URL
# The URL of your Qdrant Cloud cluster.
# Format: https://xxxx-xxxx.aws.cloud.qdrant.io
# Found in: Qdrant Cloud dashboard → your cluster → Connection details
# -----------------------------------------------------------------------
QDRANT_URL: str = os.getenv("QDRANT_URL", "")

# -----------------------------------------------------------------------
# QDRANT_API_KEY
# The API key for your Qdrant Cloud cluster.
# Found in: Qdrant Cloud dashboard → your cluster → API Keys
# -----------------------------------------------------------------------
QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")

# -----------------------------------------------------------------------
# QDRANT_METADATA_COLLECTION
# The collection name for storing repositories metadata
# -----------------------------------------------------------------------
QDRANT_METADATA_COLLECTION = "repo_metadata"

# -----------------------------------------------------------------------
# TMP_DIR
# Where cloned repos are stored temporarily during processing.
# Uses os.path.join so it works on both Windows (backslash) and Linux (slash).
# os.path.dirname(__file__) = the folder this config.py file lives in
# So TMP_DIR always points to /your-project/tmp/ regardless of where
# you run the server from.
# -----------------------------------------------------------------------
TMP_DIR: str = os.path.join(os.path.dirname(__file__), "tmp")

# -----------------------------------------------------------------------
# MAX_FILES
# Safety limit — prevents enormous repos from taking 10 minutes to index.
# 500 files is enough to demonstrate the system on any real project.
# You can raise this later once you've confirmed Railway memory stays stable.
# -----------------------------------------------------------------------
MAX_FILES: int = int(os.getenv("MAX_FILES", "500"))


# -----------------------------------------------------------------------
# STARTUP VALIDATION
# This runs once when the module is first imported (at server startup).
# If any required key is missing, the server refuses to start and prints
# exactly which key is missing. Much better than a confusing error
# 3 requests later when the key is actually needed.
# -----------------------------------------------------------------------
def validate_config() -> None:
    """
    Call this in main.py on startup.
    Raises ValueError immediately if any required env var is missing.
    """
    required = {
        # "GEMINI_API_KEY": GEMINI_API_KEY,
        "NVIDIA_API_KEY": NVIDIA_API_KEY,
        "QDRANT_URL": QDRANT_URL,
        "QDRANT_API_KEY": QDRANT_API_KEY,
    }

    missing = [key for key, value in required.items() if not value]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Add them to your .env file (local) or Railway Variables tab (production)."
        )