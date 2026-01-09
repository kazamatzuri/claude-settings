# Jira Ticket Refinement Skill - Installation Guide

Text-based backlog refinement for Claude Code.

## Prerequisites

- Python 3.10+
- Jira Cloud account with API token

## Quick Install

```bash
cd ~/.claude/skills/jira-refinement

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Jira Configuration

### 1. Create API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it "Claude Refinement" and copy the token

### 2. Configure Environment

Create `.env` file in the skill directory:

```bash
cd ~/.claude/skills/jira-refinement
cp .env.example .env
# Edit .env with your values
```

**Required settings:**
```bash
# Jira Connection
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your-api-token-here

# Project Settings
JIRA_PROJECT_KEY=PROJ

# Backlog Query - customize for your workflow
JIRA_BACKLOG_JQL="project = PROJ AND labels != 'ready' AND status = Backlog ORDER BY rank ASC"
```

### 3. Test Connection

```bash
source .venv/bin/activate
python scripts/jira_api.py test-connection
```


## Ticket Display

Tickets are opened directly in Chrome via `python scripts/display_ticket.py PROJ-123`.
No files are written - the user views and edits tickets in Jira's web interface.

## Directory Structure

```
~/.claude/skills/jira-refinement/
├── SKILL.md              # Main skill instructions
├── README.md             # This file
├── .env                  # Your configuration (create from .env.example)
├── .env.example          # Template configuration
├── requirements.txt      # Python dependencies
├── references/
│   └── ticket-template.md  # Required fields for ready tickets
└── scripts/
    ├── jira_api.py       # Jira API operations
    └── display_ticket.py # Opens ticket in browser
```

## Troubleshooting

### "Jira API returns 401"

- Verify your API token is correct
- Ensure you're using your email, not username
- Check the token hasn't expired

### "Transition not found"

- Different Jira workflows have different transition names
- Run `get-ticket PROJ-123` to see the ticket's current state
- Check your Jira project's workflow configuration

## Claude Code Permissions

To avoid being prompted for permission every session, add the skill directory to your allowed commands in `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(cd ~/.claude/skills/jira-refinement:*)",
      "Bash(cd /Users/YOUR_USERNAME/.claude/skills/jira-refinement:*)"
    ],
    "additionalDirectories": [
      "/Users/YOUR_USERNAME/.claude/skills/jira-refinement"
    ]
  },
  "sandbox": {
    "enabled": false
  }
}
```

Replace `YOUR_USERNAME` with your actual username.

**Note:** Sandbox must be disabled (`enabled: false`) because this skill makes outbound network requests to Jira, which are blocked by the sandbox.

## Usage

Once installed, trigger the skill by asking Claude:

- "Let's refine the backlog"
- "Start ticket refinement"
- "Help me groom these tickets"
- "Review non-ready tickets"

The skill will fetch tickets from your backlog and guide you through the refinement process.
