# Technical reference

## Stack

| Concern | Library | Why visible in code |
|---|---|---|
| UI | Streamlit | `st.*` throughout `app.py`; Streamlit re-executes the entire script on every user interaction — `Settings` is rebuilt from widget values on each rerun |
| Agent orchestration | LangGraph `StateGraph` | `graph.py` — two separate compiled graphs (`build_analysis_graph`, `build_qa_graph`) |
| LLM client — OpenAI-compatible | `langchain-openai` `ChatOpenAI` | `config.py:89–102`; used for both OpenAI and Agnes AI (same code path, different key env var and base URL) |
| LLM client — local | `langchain-ollama` `ChatOllama` | `config.py:134–140`; model list probed live at `{base_url}/api/tags` on every sidebar render |
| LLM client — Gemini | `langchain-google-genai` `ChatGoogleGenerativeAI` | `config.py:105–111` |
| Repo cloning | `GitPython` | `tools.py:33–53`; shallow clone (depth=1) |
| Zip extraction | `zipfile` (stdlib) | `tools.py:65–89` |
| Env config | `python-dotenv` | `config.py:13`; `.env` is loaded once at import time |
| Dependency management | `uv` | `pyproject.toml` + `uv.lock`; `run.cmd` calls `uv sync` before launch |

Python ≥ 3.11 required (`pyproject.toml:4`).

## Module dependency graph

```
app.py  →  graph.py  →  agents.py  →  tools.py
              ↓                ↓
           config.py  ←────────┘
```

- `app.py` never imports `agents.py` directly; graph execution is opaque to the UI layer.
- `tools.py` imports only two constants from `config.py` (`IGNORED_DIR_NAMES`, `KEY_FILE_PRIORITY`). It has no LangChain dependency and can be tested without an LLM.
- `agents.py` is the only module that calls `.invoke()` on an LLM client.

## Important invariants

No persistent storage. All analysis state lives in `st.session_state` for the lifetime of one browser session (`app.py:15–18`). Closing or refreshing the browser tab loses the session.

No API surface. The app is a consumer of LLM APIs; it does not expose one. It calls out to OpenAI-compatible endpoints, the Gemini API, or a local Ollama server.

No tests, no CI. Confirmed absent: no `.github/workflows`, no `pytest` configuration, no test files.

File content truncation. `tools.read_file_text` truncates to `Settings.max_file_chars` (default 6 000 characters). This cap is not configurable from the sidebar UI.

Synchronous execution. The analysis graph runs synchronously inside the Streamlit button handler; there is no background worker or async execution (`app.py:163`).

## Error handling

Every LangGraph node function follows a single contract: on failure it returns `{"error": "<message>"}` and exits early; on success it returns its output fields with `"error"` absent. The graph's `_route_on_error` function (`graph.py:35–36`) checks this field to decide whether to continue to the next node or short-circuit to `END`. The UI layer also inspects each streamed chunk for `"error"` to update the progress display, but actual control flow is handled by the graph.

Per-file summarization failures in `summarize_codebase_node` are isolated: one file's failure is recorded as the summary value for that file and does not abort the node (`agents.py:76`).

## Filesystem safety

Three mechanisms protect the host filesystem:

1. **GitHub URL allowlist** (`tools.py:13–15`, `24–30`) — a strict regex requires the `https://github.com/<owner>/<repo>` shape before any URL reaches `git.Repo.clone_from`.
2. **Zip-slip guard** (`tools.py:73–78`) — each member's resolved path is checked to remain inside the extraction directory before `extractall` is called.
3. **Delete-scope guard** (`tools.py:155–164`) — `cleanup_temp_dir` resolves the target and calls `.relative_to(TEMP_ROOT)` inside a `try/except ValueError`; any path outside `TEMP_ROOT` silently no-ops. Local folders (never copied into `TEMP_ROOT`) are therefore structurally immune to deletion.

## LLM provider routing

`config.build_strong_llm` and `config.build_fast_llm` dispatch on `Settings.strong_provider` / `Settings.fast_provider` (plain string equality). An unrecognized provider string reaches the final `return` in each function, which is the OpenAI branch — no exception is raised, and the call will fail at invocation time if `OPENAI_API_KEY` is not set.

OpenAI models are fixed to two presets; Gemini to two presets; Agnes AI to one. Ollama's model list is queried live from the server. None of these are currently configurable beyond what the sidebar exposes.

The `reasoning_effort` kwarg is passed only for the OpenAI branch, fixed at `"medium"` (`config.py:20`). It is not user-configurable.

## Q&A model routing

`agents._choose_qa_model` (`agents.py:109–115`) routes to the strong model when the question contains any substring from `QA_STRONG_KEYWORDS` (matched on the lowercased question) or exceeds 30 words. All other questions go to the fast model. The code itself notes this is a heuristic placeholder, not an intent classifier.

Only the last 6 turns of `chat_history` are included in the Q&A prompt to bound context size (`agents.py:140`).

## Temp directory lifecycle

GitHub clones and zip extractions land under `TEMP_ROOT` (`{tempdir}/codebase_understanding_agent/`), which is fixed per OS user account and shared across concurrent Streamlit sessions from the same machine. Each analysis creates a unique `tempfile.mkdtemp()` subdirectory. The app tracks the current session's temp path in `st.session_state.temp_dir_info` and deletes it on session clear or new analysis (unless "Keep cloned/extracted files after session" is checked). Local folder analyses never write to `TEMP_ROOT`.
