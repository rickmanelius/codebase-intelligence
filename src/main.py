"""CLI entry point for codebase intelligence."""

import argparse
import subprocess
import sys

from .config import load_config


def check_gh_cli() -> bool:
    """Check that gh CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def validate(config) -> bool:
    """Validate all credentials and report status."""
    all_ok = True

    # Check gh CLI
    print("Checking gh CLI... ", end="", flush=True)
    if check_gh_cli():
        print("OK")
    else:
        print("FAIL")
        print("  Install gh CLI: https://cli.github.com/")
        print("  Then run: gh auth login")
        all_ok = False

    # Check GitHub org access
    print(f"Checking GitHub org '{config.github_org}'... ", end="", flush=True)
    result = subprocess.run(
        ["gh", "repo", "list", config.github_org, "--limit", "1", "--json", "name"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("OK")
    else:
        print("FAIL")
        print(f"  Cannot access org '{config.github_org}'. Check GITHUB_ORG and your gh auth.")
        all_ok = False

    # Check JIRA credentials
    print("Checking JIRA credentials... ", end="", flush=True)
    try:
        import requests

        resp = requests.get(
            f"{config.jira_base_url}/rest/api/3/myself",
            auth=(config.jira_email, config.jira_api_token),
            timeout=10,
        )
        if resp.status_code == 200:
            print("OK")
        elif resp.status_code == 401:
            print("FAIL")
            print("  Invalid JIRA credentials. Check JIRA_EMAIL and JIRA_API_TOKEN.")
            all_ok = False
        else:
            print(f"FAIL (HTTP {resp.status_code})")
            print(f"  Check JIRA_BASE_URL: {config.jira_base_url}")
            all_ok = False
    except requests.exceptions.ConnectionError:
        print("FAIL")
        print(f"  Cannot connect to {config.jira_base_url}. Check JIRA_BASE_URL.")
        all_ok = False

    # Check Anthropic API key
    print("Checking Anthropic API key... ", end="", flush=True)
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        client.messages.create(
            model=config.claude_model,
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        print("OK")
    except anthropic.AuthenticationError:
        print("FAIL")
        print("  Invalid ANTHROPIC_API_KEY.")
        all_ok = False
    except anthropic.BadRequestError as e:
        # Key is valid but model might not exist
        if "model" in str(e).lower():
            print(f"WARN (key OK, but model '{config.claude_model}' may not be available)")
        else:
            print(f"FAIL ({e})")
            all_ok = False

    print()
    if all_ok:
        print("All checks passed. Ready to analyze tickets.")
    else:
        print("Some checks failed. Fix the issues above and try again.")

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Multi-repo codebase intelligence system",
        epilog="Example: python -m src.main PROJ-123",
    )
    parser.add_argument(
        "ticket_id",
        nargs="?",
        help="JIRA ticket ID to analyze (e.g., PROJ-123)",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Clone/fetch all org repos before analyzing",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Check all credentials and exit",
    )
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="Read ticket IDs from file (one per line)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be analyzed without writing files",
    )

    args = parser.parse_args()

    # Load and validate config (exits on error)
    config = load_config()

    # --validate mode
    if args.validate:
        success = validate(config)
        sys.exit(0 if success else 1)

    # Determine ticket IDs to process
    ticket_ids = []
    if args.batch:
        try:
            with open(args.batch) as f:
                ticket_ids = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"Batch file not found: {args.batch}", file=sys.stderr)
            sys.exit(1)
    elif args.ticket_id:
        ticket_ids = [args.ticket_id]
    elif not args.sync:
        parser.print_help()
        sys.exit(1)

    # --sync mode
    if args.sync:
        print("Repo sync not yet implemented (Phase 2).")

    # Process tickets
    if not ticket_ids:
        if not args.sync:
            print("No ticket IDs to process.", file=sys.stderr)
            sys.exit(1)
        return

    for i, ticket_id in enumerate(ticket_ids, 1):
        prefix = f"[{i}/{len(ticket_ids)}]" if len(ticket_ids) > 1 else ""
        if args.dry_run:
            print(f"{prefix} Would analyze: {ticket_id}")
            continue

        print(f"{prefix} Analyzing {ticket_id}...")
        print("  Ticket analysis not yet implemented (Phase 2+3).")


if __name__ == "__main__":
    main()
