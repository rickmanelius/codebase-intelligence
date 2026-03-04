"""Configuration loading and validation."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


@dataclass
class Config:
    """Validated configuration from environment variables."""

    anthropic_api_key: str
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    github_org: str
    claude_model: str
    repos_dir: Path
    intel_dir: Path
    diff_max_lines: int


def load_config() -> Config:
    """Load and validate configuration from .env file and environment."""
    load_dotenv()

    errors = []

    # Required vars
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY is required")

    jira_base_url = os.getenv("JIRA_BASE_URL", "")
    if not jira_base_url:
        errors.append("JIRA_BASE_URL is required")
    elif not urlparse(jira_base_url).scheme:
        errors.append("JIRA_BASE_URL must be a valid URL (e.g., https://yourorg.atlassian.net)")

    jira_email = os.getenv("JIRA_EMAIL", "")
    if not jira_email:
        errors.append("JIRA_EMAIL is required")

    jira_api_token = os.getenv("JIRA_API_TOKEN", "")
    if not jira_api_token:
        errors.append("JIRA_API_TOKEN is required (https://id.atlassian.com/manage-profile/security/api-tokens)")

    github_org = os.getenv("GITHUB_ORG", "")
    if not github_org:
        errors.append("GITHUB_ORG is required")

    # Optional vars with defaults
    claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
    repos_dir = Path(os.getenv("REPOS_DIR", "./repos"))
    intel_dir = Path(os.getenv("INTEL_DIR", "./intel"))

    diff_max_lines_str = os.getenv("DIFF_MAX_LINES", "500")
    try:
        diff_max_lines = int(diff_max_lines_str)
    except ValueError:
        errors.append(f"DIFF_MAX_LINES must be an integer, got: {diff_max_lines_str}")
        diff_max_lines = 500

    if errors:
        print("Configuration errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print("\nCopy .env.example to .env and fill in the required values.", file=sys.stderr)
        sys.exit(1)

    return Config(
        anthropic_api_key=anthropic_api_key,
        jira_base_url=jira_base_url.rstrip("/"),
        jira_email=jira_email,
        jira_api_token=jira_api_token,
        github_org=github_org,
        claude_model=claude_model,
        repos_dir=repos_dir,
        intel_dir=intel_dir,
        diff_max_lines=diff_max_lines,
    )
