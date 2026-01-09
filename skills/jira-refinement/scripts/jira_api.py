#!/usr/bin/env python3
"""
Jira API operations for ticket refinement skill.
Supports Jira Cloud REST API v3.
"""

import os
import sys
import json
import re
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


@dataclass
class JiraConfig:
    base_url: str
    email: str
    api_token: str
    project_key: str
    backlog_jql: str

    @classmethod
    def from_env(cls) -> "JiraConfig":
        base_url = os.getenv("JIRA_BASE_URL")
        email = os.getenv("JIRA_EMAIL")
        api_token = os.getenv("JIRA_API_TOKEN")
        project_key = os.getenv("JIRA_PROJECT_KEY")
        backlog_jql = os.getenv("JIRA_BACKLOG_JQL", f"project = {project_key} AND labels != 'ready' ORDER BY rank ASC")

        if not all([base_url, email, api_token]):
            raise ValueError("Missing required Jira configuration. Check .env file.")

        return cls(
            base_url=base_url.rstrip("/"),
            email=email,
            api_token=api_token,
            project_key=project_key or "",
            backlog_jql=backlog_jql,
        )


class JiraClient:
    """Jira Cloud REST API client."""

    def __init__(self, config: Optional[JiraConfig] = None):
        self.config = config or JiraConfig.from_env()
        self.session = requests.Session()
        self.session.auth = (self.config.email, self.config.api_token)
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _api_url(self, path: str) -> str:
        """Build full API URL."""
        return f"{self.config.base_url}/rest/api/3/{path.lstrip('/')}"

    def _agile_url(self, path: str) -> str:
        """Build Agile API URL."""
        return f"{self.config.base_url}/rest/agile/1.0/{path.lstrip('/')}"

    def test_connection(self) -> bool:
        """Test Jira connection."""
        try:
            response = self.session.get(self._api_url("myself"))
            response.raise_for_status()
            user = response.json()
            print(f"Connected as: {user.get('displayName', user.get('emailAddress'))}")
            return True
        except requests.RequestException as e:
            print(f"Connection failed: {e}")
            return False

    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for issues using JQL."""
        fields = [
            "summary", "description", "status", "labels", "priority",
            "issuetype", "assignee", "reporter", "created", "updated",
            "customfield_10016",  # Story points (common field ID)
            "parent", "comment",
        ]
        # Use the new /search/jql endpoint (POST /search is deprecated - 410 Gone)
        response = self.session.get(
            self._api_url("search/jql"),
            params={
                "jql": jql,
                "maxResults": max_results,
                "fields": ",".join(fields),
            },
        )
        response.raise_for_status()
        return response.json().get("issues", [])

    def get_backlog_tickets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get non-ready tickets from backlog."""
        return self.search_issues(self.config.backlog_jql, max_results=limit)

    def get_ticket(self, issue_key: str) -> Dict[str, Any]:
        """Get full ticket details."""
        response = self.session.get(
            self._api_url(f"issue/{issue_key}"),
            params={"expand": "renderedFields,names,changelog"},
        )
        response.raise_for_status()
        return response.json()

    def get_ticket_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get comments for a ticket."""
        response = self.session.get(self._api_url(f"issue/{issue_key}/comment"))
        response.raise_for_status()
        return response.json().get("comments", [])

    def update_ticket(self, issue_key: str, fields: Dict[str, Any]) -> bool:
        """Update ticket fields."""
        response = self.session.put(
            self._api_url(f"issue/{issue_key}"),
            json={"fields": fields},
        )
        response.raise_for_status()
        return True

    def add_label(self, issue_key: str, label: str) -> bool:
        """Add a label to a ticket."""
        response = self.session.put(
            self._api_url(f"issue/{issue_key}"),
            json={"update": {"labels": [{"add": label}]}},
        )
        response.raise_for_status()
        return True

    def remove_label(self, issue_key: str, label: str) -> bool:
        """Remove a label from a ticket."""
        response = self.session.put(
            self._api_url(f"issue/{issue_key}"),
            json={"update": {"labels": [{"remove": label}]}},
        )
        response.raise_for_status()
        return True

    def add_comment(self, issue_key: str, body: str) -> Dict[str, Any]:
        """Add a comment to a ticket."""
        response = self.session.post(
            self._api_url(f"issue/{issue_key}/comment"),
            json={
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": body}],
                        }
                    ],
                }
            },
        )
        response.raise_for_status()
        return response.json()

    def transition_ticket(self, issue_key: str, transition_name: str, resolution: Optional[str] = None) -> bool:
        """Transition a ticket to a new status."""
        # First, get available transitions
        response = self.session.get(self._api_url(f"issue/{issue_key}/transitions"))
        response.raise_for_status()
        transitions = response.json().get("transitions", [])

        # Find matching transition
        transition_id = None
        for t in transitions:
            if t["name"].lower() == transition_name.lower():
                transition_id = t["id"]
                break

        if not transition_id:
            available = [t["name"] for t in transitions]
            raise ValueError(f"Transition '{transition_name}' not found. Available: {available}")

        # Execute transition
        payload = {"transition": {"id": transition_id}}
        if resolution:
            payload["fields"] = {"resolution": {"name": resolution}}

        response = self.session.post(
            self._api_url(f"issue/{issue_key}/transitions"),
            json=payload,
        )
        response.raise_for_status()
        return True

    def move_rank(self, issue_key: str, direction: str = "down", spots: int = 10) -> bool:
        """
        Move ticket position in backlog.
        Uses Jira Agile API to rerank issues.
        """
        # Get current backlog to find reference issues
        issues = self.search_issues(self.config.backlog_jql, max_results=spots + 50)

        # Find current position
        current_pos = None
        for i, issue in enumerate(issues):
            if issue["key"] == issue_key:
                current_pos = i
                break

        if current_pos is None:
            raise ValueError(f"Issue {issue_key} not found in backlog")

        # Calculate new position
        if direction == "down":
            new_pos = min(current_pos + spots, len(issues) - 1)
        else:
            new_pos = max(current_pos - spots, 0)

        if new_pos == current_pos:
            return True  # Already at target position

        # Get the issue to rank before/after
        if direction == "down" and new_pos < len(issues):
            rank_after = issues[new_pos]["key"]
            payload = {"issues": [issue_key], "rankAfterIssue": rank_after}
        elif direction == "up" and new_pos > 0:
            rank_before = issues[new_pos - 1]["key"]
            payload = {"issues": [issue_key], "rankBeforeIssue": rank_before}
        else:
            return True  # Edge case, already at boundary

        response = self.session.put(self._agile_url("issue/rank"), json=payload)
        response.raise_for_status()
        return True

    def search_epics(self, query: str) -> List[Dict[str, Any]]:
        """Search for epics matching a query."""
        jql = f"project = {self.config.project_key} AND type = Epic AND summary ~ '{query}' ORDER BY updated DESC"
        return self.search_issues(jql, max_results=10)

    def link_to_epic(self, issue_key: str, epic_key: str) -> bool:
        """Link an issue to an epic (set parent)."""
        response = self.session.put(
            self._api_url(f"issue/{issue_key}"),
            json={"fields": {"parent": {"key": epic_key}}},
        )
        response.raise_for_status()
        return True

    def create_issue_link(self, from_key: str, to_key: str, link_type: str = "Relates") -> bool:
        """Create a link between two issues."""
        response = self.session.post(
            self._api_url("issueLink"),
            json={
                "type": {"name": link_type},
                "inwardIssue": {"key": from_key},
                "outwardIssue": {"key": to_key},
            },
        )
        response.raise_for_status()
        return True

    def get_browse_url(self, issue_key: str) -> str:
        """Get the browser URL for a ticket."""
        return f"{self.config.base_url}/browse/{issue_key}"


def text_to_adf_content(text: str) -> List[Dict[str, Any]]:
    """Convert text with URLs to ADF content nodes with proper link marks.

    URLs in the text will become clickable links in Jira.
    Supports markdown-style links [text](url) and plain URLs.
    """
    # Pattern for markdown links [text](url)
    md_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    # Pattern for plain URLs
    url_pattern = r'(https?://[^\s<>\[\]]+)'

    nodes = []

    # First, handle markdown-style links
    last_end = 0
    for match in re.finditer(md_link_pattern, text):
        # Add text before the link
        if match.start() > last_end:
            before_text = text[last_end:match.start()]
            # Process plain URLs in the before_text
            nodes.extend(_process_plain_urls(before_text))

        # Add the markdown link
        link_text = match.group(1)
        link_url = match.group(2)
        nodes.append({
            "type": "text",
            "text": link_text,
            "marks": [{"type": "link", "attrs": {"href": link_url}}]
        })
        last_end = match.end()

    # Handle remaining text after last markdown link
    if last_end < len(text):
        remaining = text[last_end:]
        nodes.extend(_process_plain_urls(remaining))

    # If no nodes were created (no links), just return plain text
    if not nodes and text:
        return [{"type": "text", "text": text}]

    return nodes


def _process_plain_urls(text: str) -> List[Dict[str, Any]]:
    """Process plain URLs in text and convert them to link nodes."""
    url_pattern = r'(https?://[^\s<>\[\]]+)'
    nodes = []
    last_end = 0

    for match in re.finditer(url_pattern, text):
        # Add text before the URL
        if match.start() > last_end:
            before_text = text[last_end:match.start()]
            if before_text:
                nodes.append({"type": "text", "text": before_text})

        # Add the URL as a link
        url = match.group(1)
        nodes.append({
            "type": "text",
            "text": url,
            "marks": [{"type": "link", "attrs": {"href": url}}]
        })
        last_end = match.end()

    # Add remaining text
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining:
            nodes.append({"type": "text", "text": remaining})

    return nodes


def text_to_adf(text: str) -> Dict[str, Any]:
    """Convert plain text (with optional URLs) to Atlassian Document Format.

    Supports:
    - Newlines (converted to separate paragraphs)
    - Plain URLs (converted to clickable links)
    - Markdown-style links [text](url)
    """
    lines = text.split("\n")
    content = []

    for line in lines:
        if line.strip():
            paragraph_content = text_to_adf_content(line)
            content.append({
                "type": "paragraph",
                "content": paragraph_content
            })
        else:
            # Empty line = empty paragraph
            content.append({"type": "paragraph", "content": []})

    return {
        "type": "doc",
        "version": 1,
        "content": content
    }


def format_ticket_for_display(ticket: Dict[str, Any]) -> str:
    """Format a ticket as markdown for display."""
    fields = ticket.get("fields") or {}
    key = ticket.get("key", "Unknown")

    # Extract fields (handle None values that masquerade as empty dicts)
    summary = fields.get("summary") or "No summary"
    description = fields.get("description")
    status = (fields.get("status") or {}).get("name", "Unknown")
    issue_type = (fields.get("issuetype") or {}).get("name", "Unknown")
    priority = (fields.get("priority") or {}).get("name", "Unknown")
    labels = fields.get("labels") or []
    assignee = fields.get("assignee")
    assignee_name = (assignee.get("displayName") if assignee else None) or "Unassigned"
    story_points = fields.get("customfield_10016")
    parent = fields.get("parent")
    parent_key = (parent.get("key") if parent else None) or ""

    # Format description (handle Atlassian Document Format)
    desc_text = "No description"
    if description:
        if isinstance(description, dict):
            # ADF format - extract text
            desc_text = extract_adf_text(description)
        else:
            desc_text = description

    # Build markdown
    md = f"""# {key}: {summary}

**Type:** {issue_type} | **Status:** {status} | **Priority:** {priority}
**Assignee:** {assignee_name}
**Labels:** {', '.join(labels) if labels else 'None'}
**Story Points:** {story_points if story_points else 'Not estimated'}
**Epic:** {parent_key if parent_key else 'None'}

---

## Description

{desc_text}

---

## Acceptance Criteria

<!-- Add acceptance criteria here -->

---

## Notes

<!-- Add any notes from refinement conversation -->

"""
    return md


def extract_adf_text(adf: Dict[str, Any]) -> str:
    """Extract text from Atlassian Document Format, preserving links and mentions as markdown.

    Handles:
    - Plain text
    - Links (converted to markdown [text](url))
    - Inline cards (Jira ticket references)
    - Mentions (@username)
    - Lists (bullet and numbered)
    """
    if not adf:
        return ""

    text_parts = []

    def extract_content(node, list_prefix=""):
        # Skip None nodes
        if node is None:
            return

        if isinstance(node, dict):
            node_type = node.get("type")

            if node_type == "text":
                text = node.get("text", "")
                marks = node.get("marks") or []

                # Check for link mark (filter out None marks)
                link_mark = next((m for m in marks if m and m.get("type") == "link"), None)
                if link_mark:
                    attrs = link_mark.get("attrs") or {}
                    href = attrs.get("href", "")
                    if href:
                        text_parts.append(f"[{text}]({href})")
                    else:
                        text_parts.append(text)
                else:
                    text_parts.append(text)

            elif node_type == "inlineCard":
                # Jira ticket references and other inline cards
                attrs = node.get("attrs") or {}
                url = attrs.get("url", "")
                if url:
                    # Extract ticket key from Jira URL if possible
                    # URLs look like: https://company.atlassian.net/browse/PROJ-123
                    if "/browse/" in url:
                        ticket_key = url.split("/browse/")[-1].split("?")[0]
                        text_parts.append(f"[{ticket_key}]({url})")
                    else:
                        text_parts.append(f"[link]({url})")

            elif node_type == "mention":
                # @mentions
                attrs = node.get("attrs") or {}
                mention_text = attrs.get("text", "")
                account_id = attrs.get("id", "")
                if mention_text:
                    text_parts.append(f"@{mention_text}")
                elif account_id:
                    text_parts.append(f"@{account_id}")

            elif node_type == "hardBreak":
                text_parts.append("\n")

            elif node_type == "paragraph":
                content = node.get("content") or []
                for child in content:
                    extract_content(child)
                text_parts.append("\n")

            elif node_type == "bulletList":
                content = node.get("content") or []
                for item in content:
                    extract_content(item, list_prefix="- ")

            elif node_type == "orderedList":
                content = node.get("content") or []
                for i, item in enumerate(content, 1):
                    extract_content(item, list_prefix=f"{i}. ")

            elif node_type == "listItem":
                text_parts.append(list_prefix)
                content = node.get("content") or []
                for child in content:
                    extract_content(child)

            elif node_type == "heading":
                attrs = node.get("attrs") or {}
                level = attrs.get("level", 1)
                text_parts.append("#" * level + " ")
                content = node.get("content") or []
                for child in content:
                    extract_content(child)
                text_parts.append("\n")

            elif node_type == "codeBlock":
                text_parts.append("```\n")
                content = node.get("content") or []
                for child in content:
                    extract_content(child)
                text_parts.append("\n```\n")

            elif "content" in node:
                content = node.get("content") or []
                for child in content:
                    extract_content(child)

        elif isinstance(node, list):
            for item in node:
                extract_content(item)

    extract_content(adf)

    # Clean up extra newlines
    result = "".join(text_parts)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    return result.strip()


def main():
    """CLI interface for Jira operations."""
    import argparse

    parser = argparse.ArgumentParser(description="Jira API operations")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Test connection
    subparsers.add_parser("test-connection", help="Test Jira connection")

    # Get ticket
    get_parser = subparsers.add_parser("get-ticket", help="Get ticket details")
    get_parser.add_argument("issue_key", help="Issue key (e.g., PROJ-123)")
    get_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Get backlog
    backlog_parser = subparsers.add_parser("get-backlog", help="Get backlog tickets")
    backlog_parser.add_argument("--limit", type=int, default=10, help="Max tickets to fetch")
    backlog_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Add label
    label_parser = subparsers.add_parser("add-label", help="Add label to ticket")
    label_parser.add_argument("issue_key", help="Issue key")
    label_parser.add_argument("label", help="Label to add")

    # Add comment
    comment_parser = subparsers.add_parser("add-comment", help="Add comment to ticket")
    comment_parser.add_argument("issue_key", help="Issue key")
    comment_parser.add_argument("comment", help="Comment text")

    # Move rank
    rank_parser = subparsers.add_parser("move-rank", help="Move ticket in backlog")
    rank_parser.add_argument("issue_key", help="Issue key")
    rank_parser.add_argument("--down", type=int, help="Move down N spots")
    rank_parser.add_argument("--up", type=int, help="Move up N spots")

    # Link to epic
    epic_parser = subparsers.add_parser("link-epic", help="Link ticket to epic")
    epic_parser.add_argument("issue_key", help="Issue key")
    epic_parser.add_argument("epic_key", help="Epic key")

    # Transition
    trans_parser = subparsers.add_parser("transition", help="Transition ticket")
    trans_parser.add_argument("issue_key", help="Issue key")
    trans_parser.add_argument("--to", dest="status", help="Target status")
    trans_parser.add_argument("--resolution", help="Resolution (e.g., 'Won't Do')")

    # Search epics
    search_parser = subparsers.add_parser("search-epics", help="Search for epics")
    search_parser.add_argument("query", help="Search query")

    # Update ticket fields
    update_parser = subparsers.add_parser("update-ticket", help="Update ticket fields")
    update_parser.add_argument("issue_key", help="Issue key")
    update_parser.add_argument("--summary", help="New summary/title")
    update_parser.add_argument("--description", help="New description")
    update_parser.add_argument("--story-points", type=float, help="Story points estimate")
    update_parser.add_argument("--priority", help="Priority (Highest, High, Medium, Low, Lowest)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        client = JiraClient()

        if args.command == "test-connection":
            success = client.test_connection()
            sys.exit(0 if success else 1)

        elif args.command == "get-ticket":
            ticket = client.get_ticket(args.issue_key)
            if args.json:
                print(json.dumps(ticket, indent=2))
            else:
                print(format_ticket_for_display(ticket))

        elif args.command == "get-backlog":
            tickets = client.get_backlog_tickets(args.limit)
            if args.json:
                print(json.dumps(tickets, indent=2))
            else:
                for t in tickets:
                    print(f"{t['key']}: {t['fields']['summary']}")

        elif args.command == "add-label":
            client.add_label(args.issue_key, args.label)
            print(f"Added label '{args.label}' to {args.issue_key}")

        elif args.command == "add-comment":
            client.add_comment(args.issue_key, args.comment)
            print(f"Added comment to {args.issue_key}")

        elif args.command == "move-rank":
            if args.down:
                client.move_rank(args.issue_key, "down", args.down)
                print(f"Moved {args.issue_key} down {args.down} spots")
            elif args.up:
                client.move_rank(args.issue_key, "up", args.up)
                print(f"Moved {args.issue_key} up {args.up} spots")
            else:
                print("Specify --down or --up")

        elif args.command == "link-epic":
            client.link_to_epic(args.issue_key, args.epic_key)
            print(f"Linked {args.issue_key} to epic {args.epic_key}")

        elif args.command == "transition":
            if args.status:
                client.transition_ticket(args.issue_key, args.status, args.resolution)
                print(f"Transitioned {args.issue_key} to {args.status}")
            else:
                print("Specify --to status")

        elif args.command == "search-epics":
            epics = client.search_epics(args.query)
            for e in epics:
                print(f"{e['key']}: {e['fields']['summary']}")

        elif args.command == "update-ticket":
            fields = {}
            if args.summary:
                fields["summary"] = args.summary
            if args.description:
                # Convert plain text to Atlassian Document Format (with proper link support)
                fields["description"] = text_to_adf(args.description)
            if args.story_points is not None:
                fields["customfield_10016"] = args.story_points  # Story points field
            if args.priority:
                fields["priority"] = {"name": args.priority}

            if fields:
                client.update_ticket(args.issue_key, fields)
                print(f"Updated {args.issue_key}: {', '.join(fields.keys())}")
            else:
                print("No fields to update. Use --summary, --description, --story-points, or --priority")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
