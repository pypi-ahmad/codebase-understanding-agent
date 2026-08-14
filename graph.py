"""LangGraph workflow: shared state + the analysis pipeline + the Q&A graph."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

import agents


class AgentState(TypedDict, total=False):
    source_type: str  # "github" | "local" | "zip"
    source_input: str  # URL or local path (unused for zip)
    zip_bytes: bytes
    zip_name: str
    settings: Any  # config.Settings

    codebase_path: str
    file_tree: str
    key_files: list
    file_summaries: dict
    architecture_summary: str

    question: str
    answer: str
    used_model: str
    chat_history: Annotated[list, operator.add]

    error: Optional[str]


def _route_on_error(state: AgentState) -> str:
    return "stop" if state.get("error") else "continue"


def build_analysis_graph():
    graph = StateGraph(AgentState)
    graph.add_node("load_codebase", agents.load_codebase_node)
    graph.add_node("explore_structure", agents.explore_structure_node)
    graph.add_node("summarize_codebase", agents.summarize_codebase_node)
    graph.add_node("explain_architecture", agents.explain_architecture_node)

    graph.set_entry_point("load_codebase")
    graph.add_conditional_edges(
        "load_codebase", _route_on_error, {"continue": "explore_structure", "stop": END}
    )
    graph.add_conditional_edges(
        "explore_structure", _route_on_error, {"continue": "summarize_codebase", "stop": END}
    )
    graph.add_conditional_edges(
        "summarize_codebase", _route_on_error, {"continue": "explain_architecture", "stop": END}
    )
    graph.add_edge("explain_architecture", END)
    return graph.compile()


def build_qa_graph():
    graph = StateGraph(AgentState)
    graph.add_node("qa_agent", agents.qa_agent_node)
    graph.set_entry_point("qa_agent")
    graph.add_edge("qa_agent", END)
    return graph.compile()
