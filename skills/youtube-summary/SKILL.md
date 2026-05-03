---
name: youtube-summary
description: >
  Summarize a YouTube video by audio analysis with Gemini 3.1 Pro Preview. Use
  this skill when the user pastes a YouTube URL and asks for a summary, recap,
  or extracted points — including phrasings like "summarize this video",
  "what's this video about", "tl;dr this", or "give me the key points from".
  Supports short / medium / long detail levels and optional structured JSON
  output (title, summary_md, key_points, entities). Works on any video the
  channel makes audio available for; no captions required.
---

# youtube-summary

Single self-contained Python script (PEP 723 inline metadata, run via uv).
Downloads the audio track of a YouTube video, uploads it to Gemini, and returns
a structured markdown summary.

## When to use

- The user supplies a YouTube URL and asks for a summary, recap, key points,
  or any "what does this video say about X" question.
- The user wants TL;DR + bullet points without watching.
- The user wants structured extraction (entities, tickers, names) from a video.

## When **not** to use

- The user wants the full transcript verbatim — this skill summarises, not
  transcribes. Use `yt-dlp --write-auto-sub` for that.
- The user wants a different LLM. The model is configurable via `--model` but
  the skill assumes a Gemini-compatible API key.
- The video is private / region-locked / age-gated and yt-dlp can't fetch it.

## Usage

```sh
~/.claude/skills/youtube-summary/summarize.py <youtube-url>
```

Common variations:

```sh
# Quick TL;DR (~100 words)
~/.claude/skills/youtube-summary/summarize.py URL --detail short

# Detailed write-up (~600-1000 words)
~/.claude/skills/youtube-summary/summarize.py URL --detail long

# Structured JSON: { title, summary_md, key_points[], entities[] }
~/.claude/skills/youtube-summary/summarize.py URL --json

# Custom prompt — replaces the default prompt entirely
~/.claude/skills/youtube-summary/summarize.py URL --prompt ./my-prompt.md

# Pick a different Gemini model
~/.claude/skills/youtube-summary/summarize.py URL --model gemini-2.5-flash

# Write to a file instead of stdout
~/.claude/skills/youtube-summary/summarize.py URL --output summary.md

# Watch progress on stderr
~/.claude/skills/youtube-summary/summarize.py URL -v
```

The script is the only artifact — uv installs `google-genai` and `yt-dlp` into
its per-script cache on first run. No virtualenv setup needed.

## Default output shape (without `--json`)

```markdown
## TL;DR
Two or three sentences with the single most important takeaway.

## Key Points
- 4-8 substantive bullets

## Notable Details
Specific data, names, dates, prices, citations.

## Caveats / Open Questions
Hedges, contradictions, or open threads from the speaker.
```

`Notable Details` and `Caveats` are omitted when there's nothing to say there.

## API key

Resolved in this order — first hit wins:

1. `$GEMINI_API_KEY` env var
2. `$GOOGLE_API_KEY` env var
3. `~/.config/gemini/api-key` (one-line file)
4. `~/.claude/secrets/gemini-api-key` (one-line file)
5. `GEMINI_API_KEY=` line in `~/projects/stockedup-daily/.env` (legacy fallback)

Get a key at https://aistudio.google.com/apikey.

## Cost / latency rough guidance

- ~17-min video: ~50s wall time, single Gemini call
- ~60-min video: ~2-3 min wall time
- Cost scales with audio token count (Gemini meters audio at 32 tokens/sec).
  A 17-min video is roughly 33k input audio tokens.

## Source layout

- Source: `~/projects/claude-settings/skills/youtube-summary/`
- Symlink: `~/.claude/skills/youtube-summary` → above
- Single file: `summarize.py` is the entire implementation.

## Limitations

- One video per invocation (no playlists). Loop in shell if you need batch.
- The script downloads to a temp dir and cleans up — no audio cache between
  runs. Add caching if you need it for repeated analysis of the same video.
- Default prompt is general-purpose. For domain-specific extraction
  (financial analysis, medical research, etc.), pass `--prompt` with a
  tailored instruction file.
