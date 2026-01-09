#!/usr/bin/env python3
"""
Utility for opening Jira tickets in browser.

NOTE: Most display functionality is now handled natively by Claude Code:
- Fetching tickets: `python jira_api.py get-ticket PROJ-123 --json`
- Formatting markdown: Claude does this natively
- Writing files: Claude uses the Write tool

This script is retained only for opening tickets in browser.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


def open_ticket_in_browser(issue_key: str, jira_base_url: Optional[str] = None):
    """Open ticket in default browser (Chrome on macOS)."""
    if not jira_base_url:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")
        jira_base_url = os.getenv("JIRA_BASE_URL", "")

    url = f"{jira_base_url.rstrip('/')}/browse/{issue_key}"

    if sys.platform == "darwin":
        # macOS - prefer Chrome
        subprocess.run(
            ["open", "-a", "Google Chrome", url],
            check=False,
        )
    elif sys.platform == "linux":
        subprocess.run(["xdg-open", url], check=False)
    else:
        import webbrowser
        webbrowser.open(url)

    print(f"Opened: {url}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Open Jira ticket in browser")
    parser.add_argument("issue_key", help="Issue key (e.g., PROJ-123)")

    args = parser.parse_args()
    open_ticket_in_browser(args.issue_key)


if __name__ == "__main__":
    main()
