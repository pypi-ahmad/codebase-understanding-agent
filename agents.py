"""The four agent nodes: load, explore, summarize, explain, and Q&A."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

import config
import tools
from tools import ToolError

QA_STRONG_KEYWORDS = [
    "architecture", "design pattern", "design decision", "why does", "why is",
    "trade-off", "tradeoff", "scalab", "refactor", "compare", "pros and cons",
    "security", "performance", "concurrency", "best practice", "anti-pattern",
    "how would you improve", "critique",
]


def load_codebase_node(state: dict) -> dict:
    source_type = state.get("source_type")
    try:
        if source_type == "github":
            path = tools.clone_repo(state["source_input"])
        elif source_type == "local":
            path = tools.validate_local_path(state["source_input"])
        elif source_type == "zip":
            path = tools.extract_zip(state["zip_bytes"], state.get("zip_name", "upload.zip"))
        else:
            return {"error": f"Unknown source type: {source_type!r}"}
    except ToolError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error loading codebase: {e}"}
    return {"codebase_path": str(path)}


def explore_structure_node(state: dict) -> dict:
    try:
        root = Path(state["codebase_path"])
        settings: config.Settings = state["settings"]
        tree_text, files = tools.build_file_tree(root)
        if not files:
            return {"error": "No readable files found in the codebase."}
        key_files = tools.identify_key_files(files, root, settings.max_files)
    except Exception as e:
        return {"error": f"Failed to explore structure: {e}"}
    return {"file_tree": tree_text, "key_files": key_files}


def summarize_codebase_node(state: dict) -> dict:
    settings: config.Settings = state["settings"]
    try:
        llm = config.build_fast_llm(settings)
    except Exception as e:
        return {"error": f"Failed to initialize fast model: {e}"}

    summaries: dict[str, str] = {}
    for kf in state["key_files"]:
        rel_path = kf["path"]
        content = tools.read_file_text(Path(kf["abs_path"]), settings.max_file_chars)
        try:
            resp = llm.invoke([
                SystemMessage(content=(
                    "You summarize source files for a codebase-understanding tool. "
                    "Be concise and concrete about the file's purpose."
                )),
                HumanMessage(content=(
                    f"File: {rel_path}\n\nContent:\n{content}\n\n"
                    "Summarize this file's purpose and role in the project in 2-3 sentences."
                )),
            ])
            summaries[rel_path] = resp.content.strip()
        except Exception as e:
            summaries[rel_path] = f"[summary failed: {e}]"

    return {"file_summaries": summaries}


def explain_architecture_node(state: dict) -> dict:
    settings: config.Settings = state["settings"]
    try:
        llm = config.build_strong_llm(settings)
    except Exception as e:
        return {"error": f"Failed to initialize strong model: {e}"}

    summaries_block = "\n\n".join(
        f"### {path}\n{summary}" for path, summary in state["file_summaries"].items()
    )
    prompt = (
        "You are analyzing a codebase. Below is its file tree and summaries of its key files.\n\n"
        f"FILE TREE:\n{state['file_tree']}\n\n"
        f"KEY FILE SUMMARIES:\n{summaries_block}\n\n"
        "Write a high-level architecture explanation covering: overall purpose, "
        "main modules/components and how they interact, notable design patterns, "
        "the tech stack in use, and the likely entry point(s). Use clear headings."
    )
    try:
        resp = llm.invoke([
            SystemMessage(content="You are a senior software architect explaining a codebase."),
            HumanMessage(content=prompt),
        ])
    except Exception as e:
        return {"error": f"Architecture explanation failed: {e}"}
    return {"architecture_summary": resp.content.strip()}


def _choose_qa_model(question: str) -> str:
    # ponytail: keyword/length heuristic, not a classifier. Upgrade if misroutes
    # start showing up in practice (e.g. a cheap intent-classification call).
    q = question.lower()
    if any(k in q for k in QA_STRONG_KEYWORDS) or len(question.split()) > 30:
        return "strong"
    return "fast"


def qa_agent_node(state: dict) -> dict:
    question = state["question"]
    settings: config.Settings = state["settings"]
    use_strong = _choose_qa_model(question) == "strong"

    try:
        llm = config.build_strong_llm(settings) if use_strong else config.build_fast_llm(settings)
    except Exception as e:
        return {"error": f"Failed to initialize model for Q&A: {e}"}

    context = (
        f"FILE TREE:\n{state.get('file_tree', '')}\n\n"
        f"ARCHITECTURE SUMMARY:\n{state.get('architecture_summary', '')}\n\n"
        "FILE SUMMARIES:\n" + "\n".join(
            f"- {path}: {summary}" for path, summary in state.get("file_summaries", {}).items()
        )
    )

    messages = [SystemMessage(content=(
        "You answer questions about a specific codebase using only the provided "
        "context. If the context doesn't contain the answer, say so plainly."
    ))]
    for role, content in state.get("chat_history", [])[-6:]:
        messages.append(HumanMessage(content=content) if role == "user" else AIMessage(content=content))
    messages.append(HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"))

    try:
        resp = llm.invoke(messages)
        answer = resp.content.strip()
    except Exception as e:
        return {"error": f"Q&A failed: {e}"}

    return {
        "answer": answer,
        "used_model": "strong" if use_strong else "fast",
        "chat_history": [("user", question), ("assistant", answer)],
    }
