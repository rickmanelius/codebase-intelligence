"""Read and write intel files."""

from pathlib import Path

from .config import Config


def read_repo_intel(config: Config, repo_name: str) -> str | None:
    """Read existing repo intelligence file, or return None if it doesn't exist."""
    path = config.intel_dir / "repos" / f"{repo_name}.md"
    if path.exists():
        return path.read_text()
    return None


def write_repo_intel(config: Config, repo_name: str, content: str) -> Path:
    """Write repo intelligence file. Creates directories if needed."""
    path = config.intel_dir / "repos" / f"{repo_name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def write_ticket_intel(config: Config, ticket_id: str, content: str) -> Path:
    """Write ticket analysis file. Creates directories if needed."""
    path = config.intel_dir / "tickets" / f"{ticket_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path
