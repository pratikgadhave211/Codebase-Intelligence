from core.llm.client import call_llm
from core.llm.prompts import (
    EXPLAIN_ARCHITECTURE,
    format_chunks_for_prompt,
)


def parse_architecture_response(llm_response: str) -> tuple[str, str]:
    mermaid_start = llm_response.find("```mermaid")
    if mermaid_start != -1:
        mermaid_end = llm_response.find("```", mermaid_start + 10)
        summary = llm_response[:mermaid_start].strip()
        if mermaid_end != -1:
            mermaid_raw = llm_response[mermaid_start:mermaid_end]
        else:
            mermaid_raw = llm_response[mermaid_start:]
        
        # Strip out the markdown backticks manually
        mermaid_lines = [line for line in mermaid_raw.split("\n") if not line.strip().startswith("```")]
        mermaid = "\n".join(mermaid_lines).strip()
        
        # Remove any "SUMMARY:" prefix if the LLM included it
        if summary.startswith("SUMMARY:"):
            summary = summary[8:].strip()
            
        return summary, mermaid

    # Fallback: look for "flowchart TD" directly
    flowchart_start = llm_response.find("flowchart TD")
    if flowchart_start != -1:
        summary = llm_response[:flowchart_start].strip()
        mermaid = llm_response[flowchart_start:].strip()
        # Clean up any trailing markdown ticks
        mermaid = mermaid.replace("```", "").strip()
        
        if summary.startswith("SUMMARY:"):
            summary = summary[8:].strip()
            
        return summary, mermaid

    return llm_response.strip(), ""


def generate_architecture(
    chunks: list[dict],
    architecture_context: dict,
) -> tuple[str, str]:

    code_context = format_chunks_for_prompt(chunks)
    files = sorted({
        chunk["file_path"]
        for chunk in chunks
    })

    repo_structure = "\n".join(files)

    prompt = EXPLAIN_ARCHITECTURE.format(
        node_count=architecture_context["node_count"],
        edge_count=architecture_context["edge_count"],
        entry_points="\n".join(
            architecture_context["entry_points"]
        ),
        most_depended_on="\n".join(
            architecture_context["most_depended_on"]
        ),
        largest_modules="\n".join(
            architecture_context["largest_modules"]
        ),
        dependencies="\n".join(
            architecture_context["dependencies"]
        ),
        classes="\n".join(architecture_context.get("classes", [])),
        functions="\n".join(architecture_context.get("functions", [])),
        calls="\n".join(architecture_context.get("calls", [])),
        api_routes="\n".join(architecture_context.get("api_routes", [])),
        database_models="\n".join(architecture_context.get("database_models", [])),
        repo_structure=repo_structure,
        code_context=code_context,
    )

    llm_response = call_llm(
        prompt,
        temperature=0.4,
    )

    print(f"\n[DEBUG LLM RESPONSE RAW]\n{llm_response}\n[/DEBUG LLM RESPONSE RAW]\n")

    if llm_response.startswith("[LLM Error]"):
        return (
            "Architecture generation failed.",
            "flowchart TD\nA[Generation Failed] --> B[Prompt Too Large]"
        )

    summary, mermaid = (parse_architecture_response(llm_response))

    if not mermaid:
        mermaid = (
            "flowchart TD\n"
            "A[Generation Failed] --> "
            "B[Try Re-ingesting]"
        )

    return summary, mermaid