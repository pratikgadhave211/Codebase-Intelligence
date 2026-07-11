"""
LLM Client Wrapper

Provides a unified interface for interacting with LLM models via the LangChain 
NVIDIA endpoints.
"""

import time
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.messages import SystemMessage, HumanMessage

from config import HF_TOKEN

# -----------------------------------------------------------------------
# ChatHuggingFace clients.
# -----------------------------------------------------------------------
_qwen_llm = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-7B-Instruct",
    task="text-generation",
    max_new_tokens=2048,
    temperature=0.7,
    do_sample=True,
    huggingfacehub_api_token=HF_TOKEN,
)
_qwen_client = ChatHuggingFace(llm=_qwen_llm)

_deepseek_llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
    task="text-generation",
    max_new_tokens=1024,
    temperature=0.3,
    do_sample=True,
    huggingfacehub_api_token=HF_TOKEN,
)
_deepseek_client = ChatHuggingFace(llm=_deepseek_llm)

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
        response = client_to_use.invoke(messages)
        content = response.content.strip() if response.content else ""
        if not content:
            print("[client.py] Warning: LLM returned an empty string.")
            return "The AI returned an empty response. Please try asking your question again."
        return content

    except Exception as e:
        print(f"[client.py] Rate limit or error hit: {str(e)} - waiting 10s before retry...")
        time.sleep(10)

        try:
            response = client_to_use.invoke(messages)
            content = response.content.strip() if response.content else ""
            if not content:
                return "The AI returned an empty response. Please try asking your question again."
            return content
        except Exception as retry_e:
            return (
                f"[LLM Error] Failed after retry. "
                f"Details: {str(retry_e)}"
            )