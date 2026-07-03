from typing import Annotated
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage
from core.retrieval.retriever import retrieve_chunks
from core.llm.prompts import ANSWER_QUESTION, format_chunks_for_prompt
from core.storage.repo_metadata import get_repo_metadata
from core.llm.client import _deepseek_client

from langchain_core.runnables import RunnableConfig

# Define the state graph using MessagesState
# MessagesState automatically has a "messages" key which is a list of BaseMessages
builder = StateGraph(MessagesState)

def call_model(state: MessagesState, config: RunnableConfig):
    # Extract metadata from config
    repo_name = config["configurable"].get("repo_name")
    commit_hash = config["configurable"].get("commit_hash")
    
    # The latest question is the last message from the user
    latest_msg = state["messages"][-1].content
    
    # Retrieve chunks
    chunks = retrieve_chunks(
        query=latest_msg,
        repo_name=repo_name,
        top_k=5,
        commit_hash=commit_hash,
    )
    
    code_context = format_chunks_for_prompt(chunks)
    
    # Fetch architecture and dependency graph
    metadata = get_repo_metadata(repo_name)
    architecture_summary = metadata.get("mermaid", "No architecture diagram available.") if metadata else "No metadata available."
    
    # The graph_data might be too big, summary might be better. 
    # But graph_stats or summary are good representations.
    dependency_graph = metadata.get("summary", "No dependency graph summary available.") if metadata else "No metadata available."
    
    # Format system prompt
    system_prompt = ANSWER_QUESTION.format(
        architecture_summary=architecture_summary,
        dependency_graph=dependency_graph,
        code_context=code_context,
        question=latest_msg,
    )
    
    # Prepend system prompt to the messages list that goes to the LLM
    # We must filter out old system messages so we don't stack them up
    filtered_messages = [msg for msg in state["messages"] if not isinstance(msg, SystemMessage)]
    messages_for_llm = [SystemMessage(content=system_prompt)] + filtered_messages
    
    # Invoke the model
    # _deepseek_client is for QA tasks per client.py
    response = _deepseek_client.invoke(messages_for_llm)
    
    # Return the new message to append to state
    return {"messages": [response]}

builder.add_node("agent", call_model)
builder.add_edge(START, "agent")
builder.add_edge("agent", END)

# Create a global memory saver
memory = MemorySaver()
qa_graph = builder.compile(checkpointer=memory)
