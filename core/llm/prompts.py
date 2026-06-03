"""
core/llm/prompts.py — All prompt templates in one place.

Why one file for all prompts?
  When a prompt gives bad output, you fix it here.
  When you want to improve response quality, you experiment here.
  No hunting across 5 different route files.

Template syntax:
  Each prompt uses Python's .format() placeholders: {variable_name}
  Call it like: ANSWER_QUESTION.format(code_context=chunks, question=q)

Design principle for each prompt:
  1. Tell the model its role clearly
  2. Give it the code context (retrieved chunks)
  3. Give it the specific task
  4. Tell it the output format you expect
  5. Tell it to cite file names and line numbers

The "cite file and line numbers" instruction is critical.
Without it, the model makes up plausible-sounding but wrong locations.
With it, you get answers like "in src/auth.py at line 34" which are
verifiable and make the system feel trustworthy.
"""

# -----------------------------------------------------------------------
# ANSWER_QUESTION
# Used by: api/routes/query.py
# Task: Answer a natural language question about the codebase
# -----------------------------------------------------------------------
ANSWER_QUESTION = """You are an expert software engineer analysing a codebase.

Below are the most relevant code chunks retrieved from the repository,
along with their file paths and line numbers:

{code_context}

---

Based ONLY on the code above, answer this question:
{question}

Rules:
- Cite the exact file path and line number for every claim you make.
  Example: "The authentication logic is in src/auth.py at line 34."
- If the code context does not contain enough information to answer,
  say "I cannot find enough information in the indexed code to answer this."
  Do NOT guess or hallucinate.
- Be concise and technical. The person asking is a developer.
"""


# -----------------------------------------------------------------------
# FIND_BUGS
# Used by: api/routes/bugs.py
# Task: Identify potential bugs and code quality issues
# Output: Structured JSON so the frontend can render a table
# -----------------------------------------------------------------------
FIND_BUGS = """You are an expert code reviewer analysing a codebase for bugs.

Below are code chunks from the repository:

{code_context}

---

Identify potential bugs, code smells, and issues in the code above.

Return your response as a JSON array with this exact structure:
[
  {{
    "file": "src/auth.py",
    "line": 34,
    "severity": "high",
    "issue": "One sentence description of the problem",
    "suggestion": "One sentence fix or improvement"
  }}
]

Severity levels: "high" (crash/security risk), "medium" (logic error), "low" (code smell)

Rules:
- Only report real issues visible in the provided code. Do not invent issues.
- Maximum 10 issues. Prioritise by severity.
- Return ONLY the JSON array. No explanation text before or after it.
- Escape any double quotes inside strings with backslash.
"""


EXPLAIN_ARCHITECTURE = """You are a senior software architect producing a codebase map.

Your job is to describe the REAL architecture of the repository.

You MUST use information from:

1. Dependency Graph Analysis
2. Repository Structure
3. Code Samples

The Dependency Graph Analysis is the PRIMARY source of truth.

--------------------------------------------------
OUTPUT
--------------------------------------------------

Produce EXACTLY TWO sections:

SUMMARY: A concise 2-4 sentence explanation of:

- What the project does
- Main technologies used
- Major entry points
- Major subsystems

Then output a Mermaid diagram.

--------------------------------------------------
STRICT RULES
--------------------------------------------------

Use ONLY components that appear in:

- Dependency Graph Analysis
- Repository Structure
- Code Samples

DO NOT INVENT:

- Databases
- Storage layers
- Service layers
- Data layers
- Core logic
- Backend
- Frontend
- API Router
- Controllers
- Models

unless they explicitly exist in the repository.

DO NOT create generic architectural labels.

BAD:

- Core Logic
- Service Layer
- Data Models
- Storage
- Backend
- Frontend
- API Router

GOOD:

- webhook_router.py
- ai_processor.py
- weather_agent.py
- market_price_agent.py
- App.tsx
- main.py

Prefer actual file/module names from the graph.

If the dependency graph contains:

main.py -> webhook_router.py

then use those nodes directly.

Do NOT rename them.

--------------------------------------------------
MERMAID RULES
--------------------------------------------------

Start with:

```mermaid

First line:

flowchart TD

Node IDs:

- letters
- numbers
- underscores only

Valid:

A --> B
A -->|"calls"| B

Invalid:

A -->|"calls"|> B

Every referenced node must be defined.

Maximum:

- 20 nodes
- 30 edges

Subgraph names are only visual groupings.

Nodes inside subgraphs MUST be actual repository files or modules.

Example:

subgraph API["API"]
    webhook_router_py["webhook_router.py"]
end

Do NOT create nodes named:
- API
- Core
- Backend
- Frontend
- Storage
- Service

The Mermaid diagram must be valid.

--------------------------------------------------
DEPENDENCY GRAPH ANALYSIS
--------------------------------------------------

Node Count:
{node_count}

Edge Count:
{edge_count}

Entry Points:
{entry_points}

Most Depended On:
{most_depended_on}

Largest Modules:
{largest_modules}

Dependency Edges:
{dependencies}

--------------------------------------------------
REPOSITORY STRUCTURE
--------------------------------------------------

{repo_structure}

--------------------------------------------------
CODE SAMPLES
--------------------------------------------------

{code_context}

RESPOND IN EXACTLY THIS FORMAT:

SUMMARY: <summary>

```mermaid
flowchart TD
...
```
"""

# -----------------------------------------------------------------------
# SUGGEST_REFACTOR
# Used by: api/routes/query.py (when question is about improvements)
# Task: Suggest specific refactoring improvements
# -----------------------------------------------------------------------
SUGGEST_REFACTOR = """You are a senior software engineer reviewing code for improvement.

Below are code chunks from the repository:

{code_context}

---

Suggest concrete refactoring improvements for this code.

For each suggestion:
1. Name the file and function/class to improve (with line number)
2. Explain the current problem in one sentence
3. Describe the improvement in 2-3 sentences
4. If possible, show a short before/after code snippet

Focus on:
- Reducing code duplication
- Improving error handling
- Simplifying complex logic
- Better naming and readability
- Performance improvements that are obvious from the code

Maximum 5 suggestions. Prioritise impact.
"""


def format_chunks_for_prompt(chunks: list[dict]) -> str:
    """
    Formats a list of chunk dicts into a readable string for injection
    into any of the prompt templates above.

    Input: list of chunk dicts from retriever.py
    Output: formatted string like:

      --- File: src/auth.py | Function: authenticate | Lines: 14-38 ---
      def authenticate(user, pwd):
          ...

      --- File: src/models.py | Class: User | Lines: 5-45 ---
      class User:
          ...

    This format makes it easy for the LLM to cite specific locations.
    """
    if not chunks:
        return "No code context available."

    formatted_parts = []

    for chunk in chunks:
        header = (
            f"--- File: {chunk['file_path']} | "
            f"{chunk['chunk_type'].capitalize()}: {chunk['name']} | "
            f"Lines: {chunk['start_line']}-{chunk['end_line']} ---"
        )
        formatted_parts.append(f"{header}\n{chunk['text']}")

    # Join with double newline so each chunk is visually separated
    return "\n\n".join(formatted_parts)