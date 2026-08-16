# Contributing to Codebase Understanding Agent

Thanks for considering a contribution — this is a small, community-driven, hobby-scale project, and every bug report, suggestion, and pull request genuinely helps.

There's no formal process here. If something feels like overkill for the size of a change you want to make, it probably is — just open an issue or a PR and we'll figure it out together.

## Ways to contribute

- **Report a bug** — open an issue using the bug report template.
- **Suggest a feature** — open an issue using the feature request template. The [Future Improvements](README.md#future-improvements) list in the README is a good place to check first for ideas already on the radar.
- **Improve the docs** — README.md, USAGE.md, and ARCHITECTURE.md are all fair game. Docs fixes are just as welcome as code.
- **Submit code** — bug fixes, new LLM providers, small features. See below.

## Before you start coding

For anything beyond a trivial fix, open an issue first (or comment on an existing one) describing what you want to change and why. This avoids duplicate work and lets us agree on the approach before you invest time in it.

## Development setup

```bash
git clone https://github.com/pypi-ahmad/codebase-understanding-agent.git
cd codebase-understanding-agent
uv sync
cp .env.example .env   # then fill in at least one provider key
uv run streamlit run app.py --server.port 8541
```

See [README.md](README.md#installation--setup) for prerequisites and [README.md](README.md#environment-variables) for the environment variables you'll need.

## Project layout

Read [ARCHITECTURE.md](ARCHITECTURE.md) before touching `agents.py`, `graph.py`, or `config.py` — it documents the LangGraph pipeline, the provider-routing logic, and the filesystem-safety mechanisms in `tools.py`, with file+line citations. A short version:

- `app.py` — Streamlit UI only. Business logic doesn't belong here.
- `graph.py` / `agents.py` — the LangGraph state machine and its four node functions.
- `tools.py` — filesystem operations (clone, extract, scan, read). No LLM/LangChain imports — keep it that way, it's what makes this file trivially testable.
- `config.py` — `Settings` dataclass and the LLM provider factories.

## Coding style

There's no linter or formatter configured yet (no `ruff`, no CI). Until that changes, please just match the style already in the file you're editing: type hints on function signatures, `from __future__ import annotations` at the top, docstrings on modules (not on every function), and the existing quote/spacing conventions.

## Testing your change

There's no automated test suite yet (see [Future Improvements](README.md#future-improvements) — this is a known, open gap and a great first contribution if you want to add one). Until then, please manually verify your change by actually running the app:

1. Run `uv run streamlit run app.py --server.port 8541`.
2. Exercise whichever code path you touched — e.g. if you changed `tools.py`, test all three source types (GitHub URL, Local Folder, Upload Zip); if you changed `config.py`, test with whichever provider(s) you have a key for.
3. Confirm the app still starts cleanly with **no** provider key set (it should launch and only fail when you actually try to use a keyless provider) — this is a behavior the project intentionally relies on (see `run.cmd` and `config.py`'s lazy key-checking).

If you're adding a new LLM provider, see the "How to add a feature" walkthrough in [ARCHITECTURE.md](ARCHITECTURE.md#how-to-add-a-feature-worked-example-a-new-llm-provider) — it documents the exact pattern the existing providers follow.

## Submitting a pull request

- Keep PRs focused — one change per PR is much easier to review than five.
- Describe what you changed and why in the PR description; the template will prompt you.
- Update README.md/USAGE.md/ARCHITECTURE.md in the same PR if your change affects what they describe.
- Be patient — this is maintained in spare time, so review may take a bit.

## Code of conduct

Be respectful and constructive. Disagreements about approach are fine and expected; personal attacks, harassment, or bad-faith behavior are not, and issues/PRs/comments that cross that line will be closed or removed.

## No financial contributions

This project does not want or accept donations, sponsorships, or any other form of financial support. If you'd like to give back, the most valuable thing you can do is contribute code, tests, docs, or well-written bug reports. Thank you!
