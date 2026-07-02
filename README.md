# Codebase Intel

Codebase Intel is an advanced AI-powered repository analysis and architecture mapping tool. It ingests entire codebases, performs AST-aware chunking, generates dense and sparse embeddings (Hybrid Search), and interacts with advanced Large Language Models (like Qwen and DeepSeek) to analyze, summarize, and query repositories.

## Features

- **Semantic Q&A**: Ask natural language questions about your codebase using Hybrid Search (BM25 + Dense Vectors) for high precision retrieval.
- **Architecture Mapping**: Automatically generate Mermaid.js architecture diagrams of the codebase.
- **Defect Detection**: Identify potential bugs, anti-patterns, and security issues.
- **Refactoring Suggestions**: Get AI-driven suggestions for improving code quality and maintainability.
- **AST-Aware Chunking**: Intelligently parses Python and JavaScript/TypeScript using Tree-sitter to ensure embeddings capture complete functions and classes without breaking semantic boundaries.

## Architecture

The project consists of two main components:
- `backend/`: A FastAPI application that handles repository cloning, parsing, embedding (using Qdrant and FastEmbed), and LLM interactions (via LangChain).
- `frontend/`: A React + Vite web application featuring a stunning Neobrutalist design with a real-time UI.

## Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.11+)
- Git

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows: .\.venv\Scripts\activate
   # Mac/Linux: source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your `.env` file (see `.env.example`):
   ```bash
   NVIDIA_API_KEY=your_api_key_here
   ```
5. Run the server:
   ```bash
   python -m uvicorn main:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## Design System
The frontend utilizes a custom Neobrutalist design system emphasizing high contrast, bold typography, and distinct interactive states for a premium developer experience.
