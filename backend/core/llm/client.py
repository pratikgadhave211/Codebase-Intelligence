"""
LLM Client Wrapper

Provides a unified interface for interacting with LLM models via the LangChain 
NVIDIA endpoints.
"""

import time
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import SystemMessage, HumanMessage

from config import NVIDIA_API_KEY

# -----------------------------------------------------------------------
# ChatNVIDIA clients.
# -----------------------------------------------------------------------
_qwen_client = ChatNVIDIA(
    model="qwen/qwen3.5-122b-a10b",
    temperature=0.7,
    nvidia_api_key=NVIDIA_API_KEY,
    max_tokens=2048
)

_deepseek_client = ChatNVIDIA(
    model="deepseek-ai/deepseek-v4-pro",
    temperature=1,
    nvidia_api_key=NVIDIA_API_KEY,
    max_tokens=2048
)

def call_llm(prompt: str, temperature: float = 0.3, task_type: str = "general") -> str:
    """
    Send a prompt to NVIDIA NIM, return the response text.

    Args:
        prompt      : The full prompt string (already has code context injected).
        temperature : Overrides the default temperature if provided.
        task_type   : Which model to use ("qa" for deepseek, else qwen).

    Returns:
        The model's response as a plain string.
        On any unrecoverable error, returns an error message string
        (never raises) so the API route can still return a clean JSON response.
    """

    messages = [
        SystemMessage(content=(
            "You are an expert software engineer and code analyst. "
            "Be precise, technical, and cite specific file names and "
            "line numbers when referencing code."
        )),
        HumanMessage(content=prompt)
    ]

    try:
        # Route to DeepSeek if this is for QA, otherwise use Qwen
        client_to_use = _deepseek_client if task_type == "qa" else _qwen_client

        # Note: ChatNVIDIA.invoke accepts temperature dynamically
        response = client_to_use.invoke(messages, temperature=temperature)
        content = response.content.strip() if response.content else ""
        if not content:
            print("[client.py] Warning: LLM returned an empty string.")
            return "The AI returned an empty response. Please try asking your question again."
        return content

    except Exception as e:
        print(f"[client.py] Rate limit or error hit: {str(e)} - waiting 10s before retry...")
        time.sleep(10)

        try:
            response = client_to_use.invoke(messages, temperature=temperature)
            content = response.content.strip() if response.content else ""
            if not content:
                return "The AI returned an empty response. Please try asking your question again."
            return content
        except Exception as retry_e:
            return (
                f"[LLM Error] Failed after retry. "
                f"Details: {str(retry_e)}"
            )