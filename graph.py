"""LangGraph workflow: shared state + the analysis pipeline + the Q&A graph.

Two separate compiled graphs are used rather than one to keep their concerns isolated:
  - analysis_graph: one-shot 4-node pipeline, run once per "Analyze Codebase" click.
  - qa_graph: single-node, compiled and invoked fresh on each chat message.

Must not: contain LLM calls or filesystem operations — those belong in agents.py and
tools.py respectively.

Read next: agents.py for the node implementations, app.py to see how the graphs are
invoked from the Streamlit UI.
"""

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
    # operator.add as the LangGraph reducer means updates are *appended* to the existing
    # list rather than replacing it. qa_agent_node returns [("user", q), ("assistant", a)],
    # which accumulates across chat turns without the node needing to read existing history.
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
    # Compiled fresh on each chat message rather than persisted across turns. Acceptable
    # for a single-node graph; revisit if the Q&A graph ever grows additional nodes with
    # non-trivial compile cost.
    graph = StateGraph(AgentState)
    graph.add_node("qa_agent", agents.qa_agent_node)
    graph.set_entry_point("qa_agent")
    graph.add_edge("qa_agent", END)
    return graph.compile()
