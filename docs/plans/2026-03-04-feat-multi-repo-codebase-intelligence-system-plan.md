---
title: "Multi-Repo Codebase Intelligence System"
type: feat
date: 2026-03-04
---

# Multi-Repo Codebase Intelligence System

## Overview

Build a standalone, clone-and-go GitHub repository that generates a **cross-repo knowledge graph** for AI coding agents. Users point it at their GitHub org and JIRA instance, and it produces per-repo intelligence files that accumulate architectural knowledge, patterns, gotchas, and integration points over time.

Inspired by [Joseph Mosby's "Notes on a Multi-Repo Codebase Intelligence System"](https://josephmosby.com/notes-on-a-multi-repo-codebase-intelligence-system/), adapted for GitHub (vs. GitLab) with a simplified dependency footprint.

## Problem Statement / Motivation

### The "Claude.md is a point in time" problem

A `Claude.md` file gives an AI agent static, manually-maintained context about a single repository. It's better than nothing, but it's:

- **Manual** — someone has to write and update it
- **Static** — it captures a moment, not an evolution
- **Single-repo** — it knows nothing about how repos interact
- **Implementation-only** — it has no idea *why* code was written

### The 3D context solution

This system adds three dimensions that `Claude.md` cannot:

| Dimension | Source | What it provides |
|---|---|---|
| **Intent** | JIRA tickets | *Why* code was written — the business context, acceptance criteria, and discussion |
| **Time** | Git diffs / PR history | *How* code evolved — what changed, what was reviewed, what patterns emerged |
| **Multi-repo** | Cross-org PR search | *Where* changes propagate — which repos are coupled, integration points, shared patterns |

**Put bluntly:** If context is critical, and a Claude.md is a "point" in time, this gives you a **3D view**.

### Compound Engineering alignment

This aligns with the [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin) philosophy: *"each unit of engineering work should make subsequent units easier."* Every ticket analyzed enriches the knowledge graph, making future AI-assisted development more informed. The intelligence compounds — running 50 tickets doesn't produce 50 thin files, it produces a few deeply-informed files that get richer with every analysis.

## Proposed Solution

### High-level approach

A Python CLI tool with minimal dependencies that:

1. Clones/syncs all repos from the target GitHub org locally
2. Fetches a JIRA ticket's metadata (summary, description, comments)
3. Searches GitHub PRs across the org that reference that ticket
4. Extracts diffs from local git repos (avoids API rate limits for diff content)
5. Sends the combined context to Claude for two-phase analysis:
   - **Phase 1:** Analyze intent vs. implementation (produces per-ticket file)
   - **Phase 2:** Upsert per-repo intelligence (merges new knowledge into existing files)
6. Writes output to `intel/` directory

### Key design decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Language** | Python 3.9+ | Universal, simple, required for `anthropic` SDK |
| **GitHub access** | `gh` CLI (subprocess) | Eliminates `PyGithub`/`requests` for GitHub; leverages user's existing auth; handles pagination |
| **JIRA access** | `requests` library | JIRA has no standard CLI; `requests` is simple and well-known |
| **LLM access** | `anthropic` SDK | Official SDK with retries, streaming, proper error handling |
| **Config** | `.env` file + `python-dotenv` | Standard pattern, familiar to everyone |
| **Local repo clones** | **Yes — clone all org repos locally** | Diffs from local git are instant and unlimited; avoids GitHub API rate limits during batch runs; gives access to full git history, blame, and file trees |
| **Output format** | Markdown files in `intel/` | Human-readable, agent-consumable, git-trackable |
| **Upsert pattern** | Pass existing file to Claude, instruct merge | Preserves accumulated knowledge; never overwrites |

### Total dependency count: 3 pip packages

```
anthropic
requests
python-dotenv
```

Plus `gh` CLI as an external prerequisite (already installed for most GitHub-using developers).

## Technical Approach

### Architecture

```
codebase-intelligence/
├── README.md                    # Inspiration, graphic, TL;DR, setup guide
├── LICENSE                      # MIT
├── .gitignore                   # .env, intel/, repos/, __pycache__, .venv/
├── .env.example                 # All required env vars with descriptions
├── requirements.txt             # anthropic, requests, python-dotenv
├── CLAUDE.md                    # Project conventions for AI agents
│
├── src/
│   ├── __init__.py
│   ├── main.py                  # CLI entry point + orchestrator
│   ├── config.py                # Env var loading + validation
│   ├── jira_client.py           # JIRA REST API v3 client
│   ├── github_client.py         # gh CLI wrapper (subprocess) + local git ops
│   ├── repo_sync.py             # Clone/fetch all org repos locally
│   ├── analyzer.py              # Claude API calls (analyze + upsert)
│   ├── writer.py                # Intel file read/write operations
│   └── templates.py             # Intel file section templates
│
├── prompts/
│   ├── analyze_ticket.md        # Phase 1 prompt: ticket + diffs → analysis
│   └── upsert_intel.md          # Phase 2 prompt: analysis + existing → updated intel
│
├── repos/                       # Local clones of org repos (gitignored)
│   ├── <repo-a>/
│   ├── <repo-b>/
│   └── ...
│
├── intel/                       # Output directory (gitignored by default)
│   ├── repos/                   # Per-repo intelligence files
│   │   └── <repo-name>.md
│   └── tickets/                 # Per-ticket analysis files
│       └── <TICKET-ID>.md
│
└── docs/
    └── plans/                   # This plan and future plans
```

### Implementation Phases

#### Phase 1: Foundation (Core Infrastructure)

**Goal:** Skeleton that loads config, validates credentials, and runs end-to-end with a single ticket.

**Tasks:**

- [ ] **Create `.gitignore`** — Exclude `.env`, `intel/`, `repos/`, `__pycache__/`, `.venv/`, `*.pyc`
- [ ] **Create `.env.example`** with all required variables:
  ```bash
  # Required
  ANTHROPIC_API_KEY=sk-ant-...        # Claude API key
  JIRA_BASE_URL=https://yourorg.atlassian.net  # JIRA instance URL
  JIRA_EMAIL=you@company.com          # JIRA account email
  JIRA_API_TOKEN=...                  # JIRA API token (https://id.atlassian.com/manage-profile/security/api-tokens)
  GITHUB_ORG=your-org                 # Target GitHub organization

  # Optional
  CLAUDE_MODEL=claude-sonnet-4-5-20250929  # Claude model (default: claude-sonnet-4-5-20250929)
  REPOS_DIR=./repos                   # Local clone directory (default: ./repos)
  INTEL_DIR=./intel                   # Output directory (default: ./intel)
  DIFF_MAX_LINES=500                  # Max lines per PR diff (default: 500)
  ```
- [ ] **Create `requirements.txt`**
  ```
  anthropic>=0.40.0
  requests>=2.31.0
  python-dotenv>=1.0.0
  ```
- [ ] **Implement `src/config.py`** — Load `.env`, validate all required vars are set, expose typed config object
  - Validate `JIRA_BASE_URL` is a valid URL
  - Validate `GITHUB_ORG` is non-empty
  - Validate `ANTHROPIC_API_KEY` starts with expected prefix
- [ ] **Implement `src/main.py`** — CLI entry point using `argparse`
  ```
  python -m src.main <TICKET-ID> [--sync] [--validate] [--batch <file>] [--dry-run]
  ```
  - `<TICKET-ID>`: Single ticket to analyze (e.g., `PROJ-123`)
  - `--sync`: Clone/fetch all org repos before analyzing (auto-runs on first use)
  - `--validate`: Check all credentials and exit
  - `--batch <file>`: Read ticket IDs from file (one per line)
  - `--dry-run`: Show what would be analyzed without writing files
- [ ] **Implement `src/writer.py`** — Read/write intel files
  - `read_repo_intel(repo_name) -> str | None` — returns existing content or None
  - `write_repo_intel(repo_name, content)` — writes to `intel/repos/<repo-name>.md`
  - `write_ticket_intel(ticket_id, content)` — writes to `intel/tickets/<TICKET-ID>.md`
  - Create directories if they don't exist

**Success criteria:** `python -m src.main --validate` checks all credentials and reports status.

#### Phase 2: Repo Sync + Data Fetching (GitHub, JIRA, Local Git)

**Goal:** Clone/sync org repos locally and fetch all raw data needed for analysis.

**Tasks:**

- [ ] **Implement `src/repo_sync.py`** — Clone and sync all org repos locally
  - `sync_all_repos() -> list[str]` — Clone new repos, fetch updates for existing ones
    - List org repos: `gh repo list <org> --no-archived --json name,sshUrl --limit 1000`
    - For each repo:
      - If not cloned: `git clone <url> repos/<repo-name>`
      - If already cloned: `git -C repos/<repo-name> fetch --all --prune`
    - Skip archived repos by default
    - Return list of repo names synced
  - `get_repo_path(repo_name) -> Path` — Return local path to a cloned repo
  - Progress reporting: `Syncing 47 repos... [23/47] cloning api-service`
  - Handle: clone failures (private repo without access), disk space

- [ ] **Implement `src/jira_client.py`**
  - `fetch_ticket(ticket_id) -> dict` — Returns summary, status, description (plain text), comments, URL
  - Parse Atlassian Document Format (ADF) descriptions into plain text (recursive text node extraction)
  - Filter comments: include human comments, exclude bot/automation comments
  - Handle errors: 404 (ticket not found), 401 (bad credentials), 403 (no access)
  - Use Basic Auth: `(JIRA_EMAIL, JIRA_API_TOKEN)` per Atlassian Cloud API

- [ ] **Implement `src/github_client.py`** — `gh` CLI for PR search + local git for diffs
  - `search_prs(ticket_id) -> list[dict]` — Search merged PRs across org referencing the ticket
    - Primary: `gh search prs "TICKET-ID" --owner=<org> --state=merged --json number,title,repository,url,mergeCommit`
    - Handle format normalization: search both `ABC-560` and `ABC 560`
    - Return: list of `{number, title, repo_name, url, merge_commit}`
  - `get_pr_diff(repo_name, pr_number) -> str` — Get diff from local clone
    - Use `gh pr view <number> --repo <owner/repo> --json mergeCommit,baseRefName` to get the merge commit SHA
    - Run `git -C repos/<repo-name> diff <base>...<merge_commit>` locally — instant, no rate limits
    - Truncate at `DIFF_MAX_LINES` (default 500)
    - Strip binary file diffs and lock file changes (filter `*.lock`, `*.min.js`, etc.)
  - `get_pr_reviews(repo_full_name, pr_number) -> list[str]` — Fetch review comments
    - `gh pr view <number> --repo <owner/repo> --json reviews,comments` (still via API — review text is small)
  - Validate `gh` CLI is installed and authenticated on startup
  - Handle: no results found, rate limiting (retry with backoff), auth errors

**Success criteria:** Given a real ticket ID, the system fetches JIRA data, finds matching PRs, and extracts diffs from local clones.

#### Phase 3: Intelligence Generation (Claude Analysis)

**Goal:** Use Claude to analyze fetched data and produce/update intelligence files.

**Tasks:**

- [ ] **Create `prompts/analyze_ticket.md`** — Phase 1 prompt
  - Input: JIRA ticket metadata + PR diffs + review comments
  - Output: Structured analysis with sections:
    - Intent (what the ticket aimed to accomplish)
    - What Changed (summary of code modifications per repo)
    - Codebase Areas Touched (which repos/packages/modules)
    - Intent vs. Implementation alignment
    - Key Insights (patterns discovered, tech debt introduced/resolved)
    - Confidence levels for each insight

- [ ] **Create `prompts/upsert_intel.md`** — Phase 2 prompt
  - Input: Phase 1 analysis + existing repo intel file (or blank template) + ticket ID + date
  - Output: Updated repo intel file with sections:
    - What This Repo Is
    - Stack & Key Dependencies
    - Architecture
    - Key Files & Their Roles
    - Established Patterns (with `confirmed: TICKET-ID` citations)
    - Known Gotchas
    - Tech Debt
    - Integration Points (cross-repo dependencies)
    - Testing Conventions
    - Active Areas of Development
    - Intelligence Sources (table: Ticket ID | Date | Contribution)
  - **Critical instruction:** Preserve existing content. Add/confirm/update — never remove unless contradicted. Pass ticket ID explicitly to prevent hallucinated citations.

- [ ] **Implement `src/templates.py`** — Blank intel file template (used when no existing file)

- [ ] **Implement `src/analyzer.py`**
  - `analyze_ticket(ticket_data, prs_data) -> str` — Phase 1 Claude call
  - `upsert_repo_intel(repo_name, ticket_id, analysis, existing_content) -> str` — Phase 2 Claude call
  - Use `anthropic` SDK with:
    - Configurable model (default: `claude-sonnet-4-5-20250929`)
    - `max_tokens=4096` for analysis, `max_tokens=8192` for intel upsert
    - Retry on rate limit (SDK handles this)
    - Log token usage for cost awareness

**Success criteria:** Running against a ticket produces a ticket analysis file and creates/updates repo intel files.

#### Phase 4: README, Polish & UX

**Goal:** Make it clone-and-go ready.

**Tasks:**

- [ ] **Write `README.md`** with:
  - Project title and one-line description
  - The user's comparison graphic (Claude.md vs. Multi-Repo Intelligence)
  - TL;DR / Value proposition section (the "3D view" framing)
  - Link to Joe Mosby's original article as inspiration
  - Link to Compound Engineering plugin for philosophical alignment
  - **Quick Start** (6 steps):
    1. Clone the repo
    2. Install Python dependencies (`pip install -r requirements.txt`)
    3. Ensure `gh` CLI is installed and authenticated (`gh auth status`)
    4. Copy `.env.example` to `.env` and fill in credentials
    5. Sync org repos: `python -m src.main --sync` (clones all org repos locally)
    6. Run: `python -m src.main PROJ-123`
  - **Configuration reference** — table of all env vars
  - **Usage examples** — single ticket, batch backfill, validate, dry-run
  - **How it works** — brief architecture explanation
  - **Output format** — what the intel files look like
  - **FAQ** — common issues (rate limits, no PRs found, JIRA Cloud vs. Server)
  - **License** (MIT)

- [ ] **Write `CLAUDE.md`** — Project conventions for AI agents working on this codebase

- [ ] **Add `--validate` command** — Test all credentials:
  - `gh auth status` — GitHub authentication
  - JIRA API test request — `GET /rest/api/3/myself`
  - Anthropic API test — list models or send minimal prompt
  - Report clear pass/fail for each with actionable fix instructions

- [ ] **Add progress logging** — For each ticket:
  ```
  Syncing repos... 47 repos (2 new, 45 fetched)
  [1/4] Fetching JIRA ticket PROJ-123...
  [2/4] Searching GitHub PRs... found 2 PRs in 2 repos
  [3/4] Extracting diffs from local clones...
  [4/4] Analyzing with Claude...
    → Writing intel/tickets/PROJ-123.md
    → Updating intel/repos/api-service.md (3 existing sources + 1 new)
    → Updating intel/repos/web-frontend.md (new file)
  Done. Token usage: 12,450 input / 3,200 output
  ```

- [ ] **Add `--batch` mode** — Read ticket IDs from a file, process sequentially with progress
  ```
  Processing 25 tickets...
  [1/25] PROJ-100 ✓ (2 PRs, 2 repos updated)
  [2/25] PROJ-101 ⚠ No PRs found, skipping repo intel
  [3/25] PROJ-102 ✓ (1 PR, 1 repo updated)
  ...
  Summary: 23 analyzed, 2 skipped (no PRs), 0 errors
  ```

- [ ] **Add error handling** for all API interactions:
  - JIRA: 401 → "Invalid JIRA credentials. Check JIRA_EMAIL and JIRA_API_TOKEN"
  - JIRA: 404 → "Ticket PROJ-123 not found. Check the ticket ID and your JIRA access"
  - GitHub: `gh` not found → "gh CLI is required. Install: https://cli.github.com/"
  - GitHub: not authenticated → "Run `gh auth login` first"
  - GitHub: no PRs found → Warning, continue with ticket-only analysis
  - Claude: rate limit → Automatic retry via SDK
  - Claude: context too large → Truncate diffs further, retry

## Alternative Approaches Considered

| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| **Pure bash (gh + curl + jq)** | Zero Python deps, truly minimal | No Anthropic SDK (must use raw curl), fragile JSON parsing, hard to maintain | Rejected — bash is great for `gh` calls but painful for JIRA ADF parsing and Claude API |
| **Node.js / TypeScript** | Good GitHub ecosystem (Octokit), strong typing | Heavier runtime, less universal than Python, no official Anthropic SDK advantage | Rejected — Python is simpler for this use case |
| **Python + PyGithub** | Typed GitHub API client | Extra dependency, PyGithub is heavy, `gh` CLI is simpler | Rejected — `gh` CLI does everything we need |
| **API-only diffs (no local clones)** | No disk usage, simpler setup | GitHub API rate limits (30 search/min, 5000 core/hr) make batch runs painful; each diff is an API call | Rejected — rate limits are the bottleneck for batch/backfill workflows |
| **Python + `gh` CLI + local clones (chosen)** | Minimal deps (3 pip packages), leverages existing `gh` auth, diffs from local git are instant and unlimited | Requires `gh` CLI + disk space for clones | **Chosen** — local clones eliminate the rate limit problem for the most expensive operation (diffs) |
| **MCP Server** | Could integrate directly with Claude Code | More complex architecture, limits non-Claude-Code usage | Deferred — could be added later as an additional interface |

## Acceptance Criteria

### Functional Requirements

- [ ] `python -m src.main PROJ-123` fetches JIRA ticket, finds GitHub PRs, analyzes with Claude, and writes intel files
- [ ] Running the same ticket twice enriches (not replaces) existing intel files
- [ ] `--validate` checks all credentials and reports clear pass/fail
- [ ] `--batch tickets.txt` processes multiple tickets with progress reporting
- [ ] `--dry-run` shows what would be analyzed without writing files
- [ ] Works with JIRA Cloud instances
- [ ] Works with GitHub organizations (public and private repos)
- [ ] Intel files include Intelligence Sources table tracking which tickets contributed

### Non-Functional Requirements

- [ ] Setup takes under 5 minutes for a developer with existing `gh` auth
- [ ] Single ticket analysis completes in under 60 seconds
- [ ] Handles orgs with 100+ repos (diffs from local clones; only PR search hits API)
- [ ] All API errors produce human-readable error messages with fix instructions
- [ ] `.env` file is `.gitignore`d to prevent credential leaks
- [ ] Total pip dependencies: 3 packages

### Quality Gates

- [ ] README includes: graphic, TL;DR, quick start, config reference, usage examples
- [ ] `.env.example` documents every variable with descriptions and format examples
- [ ] All API clients handle common error codes (401, 403, 404, 429)
- [ ] Intel file template produces consistent, well-structured markdown

## Dependencies & Prerequisites

| Dependency | Type | Version | Purpose |
|---|---|---|---|
| Python | Runtime | 3.9+ | Core language |
| `gh` CLI | External tool | 2.0+ | GitHub API access (PRs, diffs, search) |
| `anthropic` | pip package | >=0.40.0 | Claude API SDK |
| `requests` | pip package | >=2.31.0 | JIRA REST API calls |
| `python-dotenv` | pip package | >=1.0.0 | `.env` file loading |

**User-provided:**
- GitHub account with org access + `gh auth login` completed
- JIRA Cloud account with API token
- Anthropic API key with sufficient credits

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| GitHub search doesn't find PRs (naming convention mismatch) | High | High | Search both `ABC-123` and `ABC 123` formats; document required PR naming convention; show clear warning when no PRs found |
| GitHub search API rate limit (30/min) during batch runs | Medium | Low | Diffs come from local git (no API cost); only PR search and review comments hit the API; add delay between batch items |
| Large org clone takes significant disk space and time | Medium | Low | One-time cost; subsequent runs only fetch; skip archived repos; `--sync` is explicit so users control timing |
| JIRA ADF description parsing produces garbage | Medium | Medium | Recursive text extraction function; fall back to raw text if ADF parsing fails |
| Intel files grow too large for Claude context after many tickets | Low | High | Monitor file size; add truncation strategy for very large files; consider splitting into sections |
| Users commit `.env` with credentials | Medium | High | `.gitignore` includes `.env` from day one; README warns about this; `--validate` doesn't echo token values |
| `gh` CLI not installed | Medium | Low | Check on startup with clear install instructions |

## Future Considerations

These are explicitly **out of scope** for the initial implementation but worth noting:

- **MCP Server interface** — Expose intelligence as an MCP tool for direct Claude Code integration
- **Claude Code skill** — Package as a `/codebase-intel` slash command
- **GitHub Actions integration** — Auto-run on ticket completion via webhook
- **Monorepo support** — Sub-package intelligence within a single repo
- **JIRA Server/Data Center support** — Different auth mechanism
- **Linear/GitHub Issues support** — Alternative to JIRA as intent source
- **Automatic backfill** — Query JIRA for recently closed tickets, process all unanalyzed ones
- **Cross-repo dependency graph** — Visualize integration points as a Mermaid diagram
- **Staleness detection** — Flag intel files that haven't been updated in N tickets

## References & Research

### Inspiration

- [Joseph Mosby — "Notes on a Multi-Repo Codebase Intelligence System"](https://josephmosby.com/notes-on-a-multi-repo-codebase-intelligence-system/) — Original article describing the GitLab + JIRA implementation
- [Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin) — Philosophy: "each unit of engineering work should make subsequent units easier"

### Key Technical References

- [GitHub CLI (`gh`) documentation](https://cli.github.com/manual/) — PR search, diff, review commands
- [JIRA REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/) — Ticket fetching, ADF format
- [Anthropic Python SDK](https://docs.anthropic.com/en/docs/sdks/python) — Claude API integration
- [Atlassian Document Format](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/) — JIRA description parsing

### Internal

- User's comparison graphic: Claude.md approach (single-repo, static, manual) vs. Multi-Repo Intelligence (cross-repo, temporal, auto-generated)
