"""
api/routes/query.py — POST /api/v1/ask

Natural language Q&A about an indexed codebase.

Flow:
  1. Receive question + repo_name
  2. Retrieve top-5 relevant chunks from Qdrant (semantic search)
  3. Format chunks into prompt context
  4. Call Groq LLM with the ANSWER_QUESTION prompt
  5. Return answer with citation metadata
"""

from fastapi import APIRouter, HTTPException
import uuid

from api.models import AskRequest, AskResponse
from core.llm.qa_agent import qa_graph
from langchain_core.messages import HumanMessage
from core.storage.repo_metadata import get_repo_metadata

router = APIRouter()

@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question about the codebase",
    description="Retrieve relevant code chunks and generate an LLM answer with file citations.",
)
async def ask_question(request: AskRequest):
    """
    Semantic search + LLM answer for any question about the codebase.

    The answer includes exact file paths and line numbers from the
    retrieved chunks — so every claim is verifiable.

    If commit_hash is provided, only chunks from that specific version
    are returned — enabling version-specific Q&A.
    """
    
    # Check if the repo has metadata
    metadata = get_repo_metadata(request.repo_name)
    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No indexed data found for repo '{request.repo_name}'"
                + (f" at commit {request.commit_hash[:12]}..." if request.commit_hash else "")
                + ". Run POST /api/v1/ingest first."
            ),
        )

    # Use provided session_id or create a new one
    session_id = request.session_id if request.session_id else str(uuid.uuid4())
    
    config = {
        "configurable": {
            "thread_id": session_id,
            "repo_name": request.repo_name,
            "commit_hash": request.commit_hash
        }
    }
    
    # Run the langgraph agent
    # The agent handles retrieval and prepending the system prompt
    input_message = HumanMessage(content=request.question)
    
    try:
        # stream or invoke, invoke is easier here
        result = qa_graph.invoke({"messages": [input_message]}, config=config)
        
        # Extract the latest response message from the state
        final_message = result["messages"][-1].content
        chunks_used = 5  # We are retrieving top_k=5 in the agent
        
        return AskResponse(
            status="success",
            repo_name=request.repo_name,
            question=request.question,
            answer=final_message,
            chunks_used=chunks_used,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during Q&A: {str(e)}"
        )