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

from api.models import AskRequest, AskResponse
from core.retrieval.retriever import retrieve_chunks
from core.llm.client import call_llm
from core.llm.prompts import ANSWER_QUESTION, format_chunks_for_prompt

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
    """

    # Retrieve top-5 most relevant chunks for this question
    chunks = retrieve_chunks(
        query=request.question,
        repo_name=request.repo_name,
        top_k=5,
    )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No indexed data found for repo '{request.repo_name}'. "
                f"Run POST /api/v1/ingest first."
            ),
        )

    # Format chunks into the context string for the prompt
    code_context = format_chunks_for_prompt(chunks)

    # Build the full prompt with context injected
    prompt = ANSWER_QUESTION.format(
        code_context=code_context,
        question=request.question,
    )

    # Call Groq
    answer = call_llm(prompt, temperature=0.3)

    return AskResponse(
        status="success",
        repo_name=request.repo_name,
        question=request.question,
        answer=answer,
        chunks_used=len(chunks),
    )