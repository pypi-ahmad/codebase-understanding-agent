# Security Policy

This is a small, community-maintained, hobby-scale project with no dedicated security team, no automated dependency scanning, and no CI pipeline (see [ARCHITECTURE.md](ARCHITECTURE.md#commands--verification-inventory)). Please keep that in mind when relying on it — see [DISCLAIMER.md](DISCLAIMER.md) for the full "use at your own risk" terms.

## Supported versions

There are no tagged releases yet — only the latest commit on `main` is supported. If you report an issue, please confirm it against the current `main`.

## Reporting a vulnerability

If you find a security issue, please report it privately rather than opening a public issue, so it can be fixed before it's widely known:

1. Use GitHub's **[private vulnerability reporting](https://github.com/pypi-ahmad/codebase-understanding-agent/security/advisories/new)** ("Report a vulnerability" under the repo's Security tab), if available.
2. If that isn't available, open a regular GitHub issue with as little sensitive detail as possible and ask to be contacted privately — a maintainer will follow up.

This is a spare-time project, so please be patient — there's no guaranteed response time, but security reports will be prioritized over regular bug reports.

**Please do not include:** API keys, `.env` contents, or the contents of any private repository in a report, public or private.

## What's in scope

- The app's own code (`app.py`, `agents.py`, `graph.py`, `tools.py`, `config.py`).
- The safety mechanisms it relies on: the GitHub-URL allow-list, the zip-slip guard on zip extraction, and the temp-directory delete-scope guard (all documented with file+line citations in [ARCHITECTURE.md](ARCHITECTURE.md#3-filesystem-safety-in-toolspy)).

## What's out of scope

- Vulnerabilities in third-party dependencies (Streamlit, LangChain/LangGraph, GitPython, the LLM provider SDKs) — please report those upstream, to the respective project.
- The behavior or output of any LLM provider itself.
- Anything that requires you to already have local code-execution access to the machine running the app (this app never executes analyzed code — it only reads text and sends it to an LLM).

## Good security practices when running this app

- **Never commit your `.env` file or hardcode API keys.** `.env` is already covered by `.gitignore`; keys are always read from the environment (see `config.py`).
- **Prefer separate, scoped API keys** for this tool over your primary account keys where your provider supports it.
- **Be deliberate about what you point it at.** The app reads and sends file contents from whatever GitHub URL, local folder, or zip you give it to your chosen LLM provider — see [DISCLAIMER.md](DISCLAIMER.md) for what that means for private or sensitive code.
- **Keep dependencies up to date** — run `uv sync` periodically to pick up upstream security fixes, since there's no Dependabot or automated scanning configured yet.
