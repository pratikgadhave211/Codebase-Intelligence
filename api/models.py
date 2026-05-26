"""
api/models.py — Pydantic request/response schemas for every endpoint.

What Pydantic does:
  Pydantic validates incoming request data automatically.
  If a request body is missing a required field, or has the wrong type,
  FastAPI returns a clear 422 error BEFORE your route code even runs.
  No manual validation code needed.

  It also generates the JSON schema that powers the /docs Swagger UI —
  every field shows up with its type and description automatically.

Why one file for all models?
  Same reason as prompts.py — one place to change shapes.
  If the frontend changes what it sends, you update here, not in 5 routes.

Naming convention:
  *Request  → what the frontend sends IN  (request body)
  *Response → what the backend sends OUT (response body)
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional


# -----------------------------------------------------------------------
# INGEST — POST /api/v1/ingest
# Frontend sends a GitHub URL, backend runs the full pipeline.
# -----------------------------------------------------------------------

class IngestRequest(BaseModel):
    github_url: str = Field(
        ...,
        description="Public GitHub repository URL to analyse.",
        example="https://github.com/tiangolo/fastapi",
    )


class IngestResponse(BaseModel):
    status: str = Field(..., example="success")
    repo_name: str = Field(..., example="fastapi")
    files_indexed: int = Field(..., description="Number of source files found.")
    chunks_stored: int = Field(..., description="Number of code chunks embedded and stored.")
    graph_ready: bool = Field(..., description="True if dependency graph was built.")
    message: str = Field(..., example="Repository indexed successfully.")


# -----------------------------------------------------------------------
# QUERY — POST /api/v1/ask
# Frontend sends a question about a previously indexed repo.
# -----------------------------------------------------------------------

class AskRequest(BaseModel):
    repo_name: str = Field(
        ...,
        description="The repo name as returned by /ingest.",
        example="fastapi",
    )
    question: str = Field(
        ...,
        description="Natural language question about the codebase.",
        example="Where is the authentication logic handled?",
    )


class AskResponse(BaseModel):
    status: str = Field(..., example="success")
    repo_name: str
    question: str
    answer: str = Field(..., description="LLM-generated answer with file citations.")
    chunks_used: int = Field(..., description="Number of code chunks used as context.")


# -----------------------------------------------------------------------
# GRAPH — GET /api/v1/graph?repo_name=fastapi
# Returns the interactive dependency graph as an HTML string.
# -----------------------------------------------------------------------

class GraphResponse(BaseModel):
    status: str
    repo_name: str
    html: str = Field(..., description="Self-contained Pyvis HTML for iframe rendering.")
    stats: dict = Field(..., description="Graph statistics: nodes, edges, cycles, most_depended_on.")


# -----------------------------------------------------------------------
# BUGS — GET /api/v1/bugs?repo_name=fastapi
# Returns a list of detected issues in the codebase.
# -----------------------------------------------------------------------

class BugItem(BaseModel):
    file: str = Field(..., example="src/auth.py")
    line: int = Field(..., example=34)
    severity: str = Field(..., example="high")   # "high", "medium", "low"
    issue: str = Field(..., example="Unhandled exception in database call.")
    suggestion: str = Field(..., example="Wrap in try/except and log the error.")


class BugsResponse(BaseModel):
    status: str
    repo_name: str
    bugs: list[BugItem]
    total: int = Field(..., description="Total number of issues found.")


# -----------------------------------------------------------------------
# DIAGRAM — GET /api/v1/diagram?repo_name=fastapi
# Returns architecture summary + Mermaid diagram syntax.
# -----------------------------------------------------------------------

class DiagramResponse(BaseModel):
    status: str
    repo_name: str
    summary: str = Field(..., description="3-5 sentence architecture overview.")
    mermaid: str = Field(..., description="Mermaid flowchart syntax string for frontend rendering.")


# -----------------------------------------------------------------------
# ERROR — used by all routes when something goes wrong.
# Returned with appropriate HTTP status codes (400, 404, 500).
# -----------------------------------------------------------------------

class ErrorResponse(BaseModel):
    status: str = Field(default="error")
    message: str