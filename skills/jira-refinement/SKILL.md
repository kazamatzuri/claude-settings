---
name: jira-refinement
description: This skill should be used for Jira backlog refinement via text conversation. It pulls non-ready tickets, facilitates requirements discussion, and marks tickets ready when complete.
---

# Jira Ticket Refinement

Interactive backlog refinement workflow to prepare Jira tickets for sprint planning.

## Purpose

Facilitate ticket refinement sessions by pulling non-ready tickets from the backlog, discussing requirements with the user, updating ticket fields, and marking tickets ready when complete.

## When to Use

- User requests backlog refinement or ticket grooming
- User wants to review non-ready tickets
- User mentions "refine", "groom", or "ready" in context of tickets
- User says "let's refine the backlog" or "start ticket refinement"

## Workflow

### Fetch Backlog

```bash
cd ~/.claude/skills/jira-refinement && source .venv/bin/activate && python scripts/jira_api.py get-backlog --limit 5
```

### Get Ticket Details

```bash
cd ~/.claude/skills/jira-refinement && source .venv/bin/activate && python scripts/jira_api.py get-ticket PROJ-123
```

### Display Format

Present each ticket as:
```
## PROJ-123: [Summary]
**Status:** Backlog | **Priority:** Medium | **Epic:** PROJ-100
**What it's about:** [Brief colloquial description]
**What's missing:** [Missing fields - acceptance criteria, story points, etc.]
```

## Commands

| User Says | Action | Script |
|-----------|--------|--------|
| "Save it" / "Done" / "Ready" | Transition to Ready | `transition PROJ-123 --to Ready` |
| "Won't do" / "Close it" | Close ticket | `transition PROJ-123 --to Done --resolution "Won't Do"` |
| "Update description to [text]" | Update description | `update-ticket PROJ-123 --description "text"` |
| "Set story points to N" | Set estimate | `update-ticket PROJ-123 --story-points N` |
| "Set priority to [level]" | Set priority | `update-ticket PROJ-123 --priority High` |
| "Move down N" | Rerank in backlog | `move-rank PROJ-123 --down N` |
| "Link to [epic]" | Link to epic | `link-epic PROJ-123 EPIC-456` |
| "Add comment: [text]" | Add discussion note | `add-comment PROJ-123 "text"` |
| "Open in browser" | View in Jira | `python scripts/display_ticket.py PROJ-123` |
| "Next" / "Skip" | Next ticket | - |
| "End session" | Stop | - |

All script commands run from the skill directory with venv activated:
```bash
cd ~/.claude/skills/jira-refinement && source .venv/bin/activate && python scripts/jira_api.py [command]
```

## Ready Ticket Requirements

Before marking a ticket "Ready", load and verify against `references/ticket-template.md`. A ticket needs:
- Clear problem statement
- Acceptance criteria (outcomes, not tasks)
- Appropriate priority
- Labels and blockers identified

## Critical Rules

**Use the correct command for each operation:**

| Operation | Correct | WRONG |
|-----------|---------|-------|
| Mark ready | `transition --to Ready` | ~~add-comment "ready"~~ |
| Update description | `update-ticket --description` | ~~add-comment "new desc"~~ |
| Close ticket | `transition --to Done` | ~~add-comment "won't do"~~ |

- **NEVER use `add-comment` for status changes or field updates**
- **Comments are ONLY for discussion notes**
- **NEVER read or check .env files** - scripts handle config automatically
- **DO NOT write any files** - open tickets in browser instead

## Error Handling

| Error | Resolution |
|-------|------------|
| 401 Unauthorized | Credentials may be expired. Ask user to verify their Jira API token. |
| Transition not found | Run `get-ticket` to see available transitions for that ticket's current state. |
| Field update fails | Some fields may be read-only or require specific values. Check Jira project configuration. |
