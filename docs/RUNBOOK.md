# Runbook

## Start

**Windows (one-click):**

```
run.cmd
```

Runs `uv sync`, warns if `OPENAI_API_KEY` is unset, then launches on port 8541.

**Any OS (manual):**

```bash
uv sync
uv run streamlit run app.py --server.port 8541
```

App opens at `http://localhost:8541`. There is no daemon mode; the process runs in the foreground.

## Stop

Press `Ctrl+C` in the terminal where the app is running.

Temp directories (GitHub clones and zip extractions) are not automatically deleted on stop unless the user clicked "Delete cloned/extracted files now" or "Clear session" in the UI before stopping. Files remaining in `{tempdir}/codebase_understanding_agent/` can be deleted manually.

## Logs

No logging module is configured. Streamlit writes its own startup and error output to stdout/stderr. LLM errors surface as `st.error()` in the UI; they are not written to a file.

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `OPENAI_API_KEY environment variable is not set.` | The selected provider's key is missing | Set the environment variable or add it to `.env` |
| `GOOGLE_API_KEY environment variable is not set.` | Gemini selected with no key | Same as above for `GOOGLE_API_KEY` |
| `AGNES_API_KEY environment variable is not set.` | Agnes AI selected with no key | Same as above for `AGNES_API_KEY` |
| `Repository not found or private: <url>` | The GitHub repo is private or the URL is wrong | Use a public repo URL; private repos are not supported |
| `Not a valid public GitHub repo URL.` | URL does not match `https://github.com/<owner>/<repo>` | Use the exact HTTPS format; SSH and `git://` URLs are rejected |
| `Git clone failed: …` | Network failure, git not on PATH, or other git error | Check network access; confirm `git` is installed |
| `Not a valid zip file: <name>` | Uploaded file is corrupt or not a zip | Re-create or re-download the zip |
| `Unsafe path in zip, aborted: <path>` | Zip contains a path that would escape the extraction directory (zip-slip attempt) | Use a clean zip archive |
| `No readable files found in the codebase.` | The source directory is empty or every file was filtered out | Check the path; all files may be under an excluded directory (`.git`, `node_modules`, etc.) |
| `Failed to initialize fast model: …` | Provider key missing or network failure before summarization | Set the key for the selected fast-model provider |
| `Failed to initialize strong model: …` | Same, for the strong-model provider | Set the key for the selected strong-model provider |
| `Architecture explanation failed: …` | LLM API error during the final pipeline step | Check API key validity and provider status |
| Ollama dropdown shows "Ollama not reachable" | Ollama server is not running at the configured URL | Start Ollama (`ollama serve`) or correct the base URL in the sidebar |
| `Path does not exist: …` | Local-folder path entered does not exist on disk | Check the path; quote paths that contain spaces |
| `Path is not a directory: …` | A file path was entered instead of a directory | Point to the project root directory |

## Temp file cleanup

Cloned repos and extracted zips land under `{OS temp dir}/codebase_understanding_agent/`. To clean up manually:

- Locate the directory with your OS's temp path (`%TEMP%` on Windows, `/tmp` or `$TMPDIR` on Unix).
- Delete the `codebase_understanding_agent/` subdirectory.

The app's `cleanup_temp_dir` function refuses to delete anything outside this directory, so local-folder paths are never at risk.
