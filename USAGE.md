# Using the Codebase Understanding Agent

A step-by-step guide to running an analysis, configuring models, reading results, and fixing the errors you might hit along the way.

For installation and environment-variable setup, see [README.md](README.md#installation--setup) and [README.md](README.md#environment-variables). For how the app works internally, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Contents

- [Launch the app](#launch-the-app)
- [Choose a source](#choose-a-source)
- [Configure models](#configure-models)
- [Run an analysis](#run-an-analysis)
- [Read the results](#read-the-results)
- [Ask questions in Chat](#ask-questions-in-chat)
- [Clean up temp files](#clean-up-temp-files)
- [Troubleshooting](#troubleshooting)
- [Example workflows](#example-workflows)

## Launch the app

Double-click `run.cmd` (Windows), or run `uv run streamlit run app.py --server.port 8541` from a terminal. The app opens at `http://localhost:8541`.

If no `OPENAI_API_KEY` is set and no `.env` file exists, `run.cmd` prints a warning but still launches — the app itself only fails when you actually try to use a provider that needs a key you haven't set.

## Choose a source

Pick one of the three radio options at the top of the page, then provide the matching input.

| Source | What to enter | What's enforced |
| --- | --- | --- |
| **GitHub URL** | A public repo URL, e.g. `https://github.com/owner/repo` | Must match `https://github.com/<owner>/<repo>`, with an optional `.git` suffix and trailing slash. Anything else (SSH URLs, other hosts, private repos) is rejected before any network call. |
| **Local Folder** | An absolute path on your machine | The path must exist and must be a directory. It is only ever read — never modified or deleted, regardless of what you do in the app afterward. |
| **Upload Zip** | A `.zip` file via the file picker | Extracted into an isolated temp folder with a zip-slip guard: any entry that would extract outside that folder aborts the whole extraction. If the zip contains one single top-level folder, that folder is treated as the project root. |

Click **Analyze Codebase**. If you haven't filled in the selected source yet, the app tells you so instead of running (`Enter a value for the selected source first.` / `Upload a zip file first.`).

## Configure models

Open the sidebar before or after analyzing — settings apply the next time you click **Analyze Codebase** or send a chat message.

**Strong model** (used for the architecture write-up and harder chat questions):
- Provider: OpenAI, Agnes AI, or Gemini.
- Model: for OpenAI and Gemini, pick from two fixed presets each; Agnes AI is fixed to one model (shown as "(fixed)").

**Fast model** (used for per-file summaries and simple chat questions):
- Provider: OpenAI, Ollama, Agnes AI, or Gemini.
- If you pick **Ollama**, set its base URL (default `http://localhost:11434`) — the sidebar queries the server live and shows a dropdown of whatever models you've already pulled there, or a warning if it's unreachable.

**Other sliders/checkboxes:**
- **Temperature** — separate sliders for strong (default 0.2) and fast (default 0.1) models, 0.0–1.0.
- **Max files to summarize** — caps how many key files the Summarizer processes, 3–30 (default 12). Lower this if analysis is taking too long on a large repo.
- **Keep cloned/extracted files after session** — unchecked by default, meaning cloned/extracted temp folders are deleted automatically when you start a new analysis or clear the session. Check it if you want to inspect the raw files afterward.

The sidebar also shows which API keys are currently set (`OPENAI_API_KEY`, `AGNES_API_KEY`, `GOOGLE_API_KEY`) so you can confirm your `.env` loaded correctly without printing the actual key values.

## Run an analysis

Clicking **Analyze Codebase** runs four steps in order, each streamed live:

1. **Explorer: loading codebase** — clones the repo, validates the local path, or extracts the zip.
2. **Explorer: building file tree & key files** — walks the tree (skipping `.git`, `node_modules`, `.venv`, and similar noise directories) and scores files by a priority list (README, manifests like `pyproject.toml`/`package.json`, entry points like `main.py`/`app.py`, Dockerfiles, etc.) up to your "Max files" setting.
3. **Summarizer: summarizing key files** — sends each key file to the fast model for a 2–3 sentence summary.
4. **Architecture Explainer: writing overview** — sends the file tree and all summaries to the strong model for a structured write-up.

Each step shows "done" or "FAILED" as it completes. If any step fails, the run stops immediately (later steps never run) and the specific error is shown in red — see [Troubleshooting](#troubleshooting).

## Read the results

Once analysis succeeds, three tabs appear:

- **Overview** — the rendered file tree, plus an expander per key file showing its summary.
- **Architecture** — the full architecture write-up from the strong model (headings, prose).
- **Chat** — see below.

## Ask questions in Chat

Type a question in the chat box at the bottom of the Chat tab. Each answer is followed by a caption showing which model answered it (`model used: fast` or `model used: strong`).

Routing is automatic and keyword/length-based: your question goes to the **strong** model if it contains a word like *architecture, design pattern, why does/is, trade-off, scalability, refactor, compare, security, performance, concurrency, best practice, anti-pattern,* or *critique* — or if it's longer than 30 words. Otherwise it goes to the **fast** model. There's no way to force one or the other per-message; if you consistently want the strong model's depth, phrase the question to include one of those trigger words or just ask it in more detail.

Chat history (up to the last 6 turns) is passed as context to every new question, along with the file tree, architecture summary, and file summaries — so follow-ups like *"why is that?"* work without re-stating context.

## Clean up temp files

At the bottom of the results area:

- **Delete cloned/extracted files now** — appears only after a GitHub or zip analysis (local folders were never copied anywhere, so there's nothing to delete for those). Removes the temp directory immediately.
- **Clear session** — resets the whole analysis (file tree, summaries, chat history) and applies the same cleanup rule as above unless "Keep cloned/extracted files after session" is checked.

Starting a *new* analysis also cleans up the previous run's temp files automatically (same "keep" rule applies).

## Troubleshooting

| Error you see | Cause | Fix |
| --- | --- | --- |
| `Not a valid public GitHub repo URL. Expected: https://github.com/<owner>/<repo>` | URL doesn't match the expected shape, or isn't `github.com` | Use the exact `https://github.com/<owner>/<repo>` form; SSH URLs and other git hosts aren't supported. |
| `Repository not found or private: <url>` | Repo doesn't exist, is misspelled, or is private | Double-check the URL; private repos aren't supported (no auth is passed to the clone). |
| `Git clone failed: ...` | Any other git failure (network, disk, etc.) | Read the truncated git error shown; usually a connectivity or disk-space issue. |
| `Path does not exist: <path>` | Local Folder path is wrong or on a different drive/mount than expected | Verify the path in a file browser or terminal first. |
| `Path is not a directory: <path>` | You pointed at a file, not a folder | Point at the folder containing the project. |
| `Not a valid zip file: <name>` | Upload wasn't a real zip (corrupted or renamed) | Re-export/re-zip the project and try again. |
| `Unsafe path in zip, aborted: <member>` | The zip contains an entry that would extract outside its target folder (zip-slip) | This is a safety rejection, not a bug in your file — re-create the zip with a normal archiver if you hit this on a file you trust. |
| `No readable files found in the codebase.` | Every file in the source was skipped or unreadable | Confirm the source actually contains files outside the ignored directories (`.git`, `node_modules`, `.venv`, etc.). |
| `Failed to initialize fast/strong model: ... environment variable is not set.` | You selected a provider whose API key env var isn't set | Set the corresponding key (`OPENAI_API_KEY`, `AGNES_API_KEY`, or `GOOGLE_API_KEY`) in `.env` or your shell, then restart the app. |
| Sidebar shows "Ollama not reachable at this URL, or no models pulled yet" | Ollama server isn't running at that base URL, or has no models pulled | Start Ollama (`ollama serve`), confirm the base URL, and `ollama pull <model>` at least one model. |
| `[summary failed: ...]` inside a file's Overview expander | That one file's summarization call failed (e.g. transient API error) | Other files are unaffected; re-run the analysis if you need that file's summary. |

## Example workflows

- Analyze `https://github.com/<owner>/<repo>`, then ask in Chat: *"What does the Summarizer agent do?"* (fast model) or *"Why was this architecture chosen?"* (routes to the strong model — contains "why").
- Point **Local Folder** at a project on disk to get a file tree and architecture summary without cloning anything, then check "Keep cloned/extracted files after session" — this has no effect for local folders since nothing is copied, but is harmless to leave checked.
- Zip up a project that isn't in Git and drop it into **Upload Zip** for the same analysis, then use **Delete cloned/extracted files now** once you're done reading the results.

<p align="center">Made with ❤️ by Ahmad Mujtaba</p>
