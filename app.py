"""Streamlit UI for the Codebase Understanding Agent."""

from __future__ import annotations

import os

import streamlit as st

import config
import tools
from graph import build_analysis_graph, build_qa_graph

st.set_page_config(page_title="Codebase Understanding Agent", layout="wide")

if "analysis_state" not in st.session_state:
    st.session_state.analysis_state = None
if "temp_dir_info" not in st.session_state:
    st.session_state.temp_dir_info = None  # (path, source_type) for cleanup


def cleanup_previous(keep: bool) -> None:
    info = st.session_state.temp_dir_info
    if info and not keep:
        path, src_type = info
        if src_type in ("github", "zip"):
            tools.cleanup_temp_dir(path)
    st.session_state.temp_dir_info = None


# ---- Sidebar: settings ----
with st.sidebar:
    st.header("Settings")
    st.subheader("Strong model (architecture & hard Q&A)")
    strong_provider_label = st.radio("Strong provider", ["OpenAI", "Agnes AI", "Gemini"], horizontal=True)
    strong_provider = {"OpenAI": "openai", "Agnes AI": "agnes", "Gemini": "gemini"}[strong_provider_label]
    if strong_provider == "agnes":
        strong_model = config.AGNES_MODEL
        st.caption(f"Model: {strong_model} (fixed)")
    elif strong_provider == "gemini":
        strong_model_label = st.selectbox("Strong model", list(config.GEMINI_MODEL_OPTIONS.keys()))
        strong_model = config.GEMINI_MODEL_OPTIONS[strong_model_label]
    else:
        strong_model_label = st.selectbox("Strong model", list(config.OPENAI_MODEL_OPTIONS.keys()))
        strong_model = config.OPENAI_MODEL_OPTIONS[strong_model_label]

    st.divider()
    st.subheader("Fast model (summaries & simple Q&A)")
    fast_provider_label = st.radio("Fast provider", ["OpenAI", "Ollama", "Agnes AI", "Gemini"], horizontal=True)
    fast_provider = {"OpenAI": "openai", "Ollama": "ollama", "Agnes AI": "agnes", "Gemini": "gemini"}[
        fast_provider_label
    ]

    if fast_provider == "ollama":
        ollama_base_url = st.text_input("Ollama base URL", value=config.DEFAULT_OLLAMA_BASE_URL)
        available_ollama_models = config.list_ollama_models(ollama_base_url)
        fast_model = config.DEFAULT_FAST_MODEL
        if available_ollama_models:
            st.success(f"Ollama reachable ({len(available_ollama_models)} model(s) found)")
            default_index = (
                available_ollama_models.index(config.DEFAULT_OLLAMA_MODEL)
                if config.DEFAULT_OLLAMA_MODEL in available_ollama_models
                else 0
            )
            ollama_model = st.selectbox("Ollama model", available_ollama_models, index=default_index)
        else:
            st.warning("Ollama not reachable at this URL, or no models pulled yet")
            ollama_model = config.DEFAULT_OLLAMA_MODEL
    else:
        if fast_provider == "agnes":
            fast_model = config.AGNES_MODEL
            st.caption(f"Model: {fast_model} (fixed)")
        elif fast_provider == "gemini":
            fast_model_label = st.selectbox("Fast model", list(config.GEMINI_MODEL_OPTIONS.keys()))
            fast_model = config.GEMINI_MODEL_OPTIONS[fast_model_label]
        else:
            fast_model_label = st.selectbox("Fast model", list(config.OPENAI_MODEL_OPTIONS.keys()))
            fast_model = config.OPENAI_MODEL_OPTIONS[fast_model_label]
        ollama_model = config.DEFAULT_OLLAMA_MODEL
        ollama_base_url = config.DEFAULT_OLLAMA_BASE_URL

    st.divider()
    temperature_strong = st.slider("Temperature (strong model)", 0.0, 1.0, 0.2, 0.1)
    temperature_fast = st.slider("Temperature (fast model)", 0.0, 1.0, 0.1, 0.1)
    max_files = st.slider("Max files to summarize", 3, 30, 12)
    keep_after = st.checkbox("Keep cloned/extracted files after session", value=False)

    st.divider()
    st.caption(f"OPENAI_API_KEY: {'set' if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}")
    st.caption(f"OPENAI_BASE_URL: {'set' if os.environ.get('OPENAI_BASE_URL') else 'default'}")
    st.caption(f"AGNES_API_KEY: {'set' if os.environ.get('AGNES_API_KEY') else 'NOT SET'}")
    st.caption(f"GOOGLE_API_KEY: {'set' if os.environ.get('GOOGLE_API_KEY') else 'NOT SET'}")

settings = config.Settings(
    strong_model=strong_model,
    strong_provider=strong_provider,
    fast_provider=fast_provider,
    fast_model=fast_model,
    ollama_model=ollama_model,
    ollama_base_url=ollama_base_url,
    temperature_strong=temperature_strong,
    temperature_fast=temperature_fast,
    max_files=max_files,
    keep_after=keep_after,
)

# ---- Main: source input ----
st.title("Codebase Understanding Agent")
source_mode = st.radio("Source", ["GitHub URL", "Local Folder", "Upload Zip"], horizontal=True)

source_type = None
source_input = None
zip_bytes = None
zip_name = None

if source_mode == "GitHub URL":
    source_type = "github"
    source_input = st.text_input("GitHub repository URL", placeholder="https://github.com/owner/repo")
elif source_mode == "Local Folder":
    source_type = "local"
    source_input = st.text_input("Local folder path", placeholder=r"D:\path\to\project")
else:
    source_type = "zip"
    uploaded = st.file_uploader("Upload a .zip of the codebase", type=["zip"])
    if uploaded is not None:
        zip_bytes = uploaded.getvalue()
        zip_name = uploaded.name

analyze_clicked = st.button("Analyze Codebase", type="primary")

if analyze_clicked:
    valid = True
    if source_type in ("github", "local") and not (source_input and source_input.strip()):
        st.error("Enter a value for the selected source first.")
        valid = False
    if source_type == "zip" and zip_bytes is None:
        st.error("Upload a zip file first.")
        valid = False

    if valid:
        cleanup_previous(keep_after)
        initial_state = {
            "source_type": source_type,
            "source_input": source_input or "",
            "settings": settings,
            "chat_history": [],
        }
        if source_type == "zip":
            initial_state["zip_bytes"] = zip_bytes
            initial_state["zip_name"] = zip_name

        step_labels = {
            "load_codebase": "Explorer: loading codebase",
            "explore_structure": "Explorer: building file tree & key files",
            "summarize_codebase": "Summarizer: summarizing key files",
            "explain_architecture": "Architecture Explainer: writing overview",
        }

        final_state = dict(initial_state)
        error_hit = None
        with st.status("Running agents...", expanded=True) as status:
            try:
                analysis_graph = build_analysis_graph()
                for chunk in analysis_graph.stream(initial_state):
                    for node_name, update in chunk.items():
                        label = step_labels.get(node_name, node_name)
                        if update.get("error"):
                            st.write(f"{label}: FAILED")
                            error_hit = update["error"]
                        else:
                            st.write(f"{label}: done")
                        final_state.update(update)
                    if error_hit:
                        break
            except Exception as e:
                error_hit = f"Unexpected failure: {e}"
            status.update(
                label="Analysis failed" if error_hit else "Analysis complete",
                state="error" if error_hit else "complete",
            )

        if error_hit:
            st.error(error_hit)
            st.session_state.analysis_state = None
        else:
            st.session_state.analysis_state = final_state
            if source_type in ("github", "zip"):
                st.session_state.temp_dir_info = (final_state["codebase_path"], source_type)

# ---- Results ----
state = st.session_state.analysis_state
if state:
    tab_overview, tab_arch, tab_chat = st.tabs(["Overview", "Architecture", "Chat"])

    with tab_overview:
        st.subheader("File Tree")
        st.code(state.get("file_tree", ""), language="text")
        st.subheader("Key Files")
        for kf in state.get("key_files", []):
            summary = state.get("file_summaries", {}).get(kf["path"], "(no summary)")
            with st.expander(kf["path"]):
                st.write(summary)

    with tab_arch:
        st.markdown(state.get("architecture_summary", "_No architecture summary available._"))

    with tab_chat:
        for role, content in state.get("chat_history", []):
            with st.chat_message("user" if role == "user" else "assistant"):
                st.markdown(content)

        if prompt := st.chat_input("Ask about this codebase..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            qa_input = {
                "file_tree": state.get("file_tree", ""),
                "architecture_summary": state.get("architecture_summary", ""),
                "file_summaries": state.get("file_summaries", {}),
                "chat_history": state.get("chat_history", []),
                "settings": settings,
                "question": prompt,
            }
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        qa_graph = build_qa_graph()
                        result = qa_graph.invoke(qa_input)
                    except Exception as e:
                        result = {"error": f"Unexpected failure: {e}"}
                if result.get("error"):
                    st.error(result["error"])
                else:
                    st.markdown(result["answer"])
                    st.caption(f"model used: {result.get('used_model', 'fast')}")
                    state["chat_history"] = result["chat_history"]

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.temp_dir_info and st.button("Delete cloned/extracted files now"):
            tools.cleanup_temp_dir(st.session_state.temp_dir_info[0])
            st.session_state.temp_dir_info = None
            st.success("Cleaned up.")
    with col2:
        if st.button("Clear session"):
            cleanup_previous(keep_after)
            st.session_state.analysis_state = None
            st.rerun()
