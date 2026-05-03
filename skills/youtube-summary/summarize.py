#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "google-genai>=0.8.0",
#   "yt-dlp>=2025.1.15",
#   "click>=8.1",
# ]
# ///
"""Summarize a YouTube video by audio analysis with Gemini.

Single self-contained script — uv's PEP 723 inline metadata installs the
dependencies on first run into a per-script cache, so this file is the only
artifact that needs to exist.

Usage:
    ./summarize.py <youtube-url> [--detail short|medium|long] [--json]
                                 [--prompt FILE] [--model MODEL_ID]
                                 [--output FILE]

Defaults: medium-detail markdown summary written to stdout.
The `--json` flag instead emits a structured JSON object with title, sections,
key points, and ticker mentions if present.

API key resolution (first hit wins):
    1. $GEMINI_API_KEY environment variable
    2. $GOOGLE_API_KEY environment variable
    3. ~/.config/gemini/api-key (one line)
    4. GEMINI_API_KEY= line in ~/projects/stockedup-daily/.env
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import click
from google import genai
from google.genai import types
from yt_dlp import YoutubeDL


DEFAULT_MODEL = "gemini-3.1-pro-preview"

DETAIL_GUIDANCE = {
    "short": "Aim for ~100 words. Just the headline takeaways.",
    "medium": "Aim for 250-400 words. Cover the main themes with brief detail.",
    "long": "Aim for 600-1000 words. Be thorough — sections, evidence, nuance.",
}

DEFAULT_PROMPT_TEMPLATE = """You are summarizing a YouTube video by listening to its audio.

Listen carefully to the entire video and produce a clean, well-structured markdown
summary.

Required structure:

  ## TL;DR
  Two or three sentences capturing the single most important takeaway.

  ## Key Points
  - Bulleted list of the main claims, arguments, or findings
  - 4-8 bullets, each one substantive and specific (not generic)

  ## Notable Details
  Any specific data, names, dates, prices, citations, or claims worth preserving.
  Skip if the video is purely conversational with no concrete details.

  ## Caveats / Open Questions
  Anything the speaker hedged, contradicted themselves on, or left open. Skip if
  there's nothing notable.

Length guidance: {length_guidance}

Markdown formatting rules:
- Each `##` heading must be on its own line, with a blank line before and after.
- Use real newlines (\\n in JSON) between paragraphs.
- Body paragraphs go on lines AFTER the heading line, never glued onto it.
- Bullet items start with `- ` at the start of a new line.

Be precise. Do not invent details that weren't stated. If the speaker is uncertain
or hedges, reflect that — don't paper over uncertainty for cleanliness.
"""

JSON_SCHEMA_HINT = """

Return your response as a JSON object with these fields:
- `title`: a short title for the video derived from its actual content (not just
  the YouTube title, which is often clickbait).
- `summary_md`: the full markdown summary above.
- `key_points`: array of strings, one per main point (matches Key Points bullets).
- `entities`: array of structured mentions with shape
  {"name": "...", "kind": "person|company|ticker|product|concept|event", "context": "..."}.
  Include only entities with substantive discussion. Skip if none.
"""


def resolve_api_key() -> str:
    for env_var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = os.environ.get(env_var, "").strip()
        if v:
            return v
    for path in (
        Path.home() / ".config" / "gemini" / "api-key",
        Path.home() / ".claude" / "secrets" / "gemini-api-key",
    ):
        if path.is_file():
            content = path.read_text().strip()
            if content:
                return content
    fallback_env = Path.home() / "projects" / "stockedup-daily" / ".env"
    if fallback_env.is_file():
        for line in fallback_env.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") and "=" in line:
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value
    raise click.ClickException(
        "No Gemini API key found. Set $GEMINI_API_KEY, or write the key to "
        "~/.config/gemini/api-key (one line).",
    )


def download_audio(url: str, dest_dir: Path) -> tuple[Path, dict]:
    """Download audio-only stream. Returns (path, info_dict)."""
    out_template = str(dest_dir / "audio.%(ext)s")
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": out_template,
        "noplaylist": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    if not info:
        raise click.ClickException(f"yt-dlp returned no info for {url}")

    matches = list(dest_dir.glob("audio.*"))
    audio = next((p for p in matches if p.suffix in (".m4a", ".opus", ".webm", ".mp3")), None)
    if audio is None:
        raise click.ClickException(f"Audio download succeeded but file is missing: {matches}")
    return audio, info


def wait_for_file_active(client: genai.Client, name: str, timeout_s: int = 180) -> object:
    deadline = time.monotonic() + timeout_s
    while True:
        f = client.files.get(name=name)
        state = getattr(f, "state", None)
        state_name = getattr(state, "name", str(state)) if state is not None else "UNKNOWN"
        if state_name == "ACTIVE":
            return f
        if state_name == "FAILED":
            raise click.ClickException(f"Gemini file processing FAILED for {name}")
        if time.monotonic() > deadline:
            raise click.ClickException(f"Timed out waiting for Gemini file (state={state_name})")
        time.sleep(2)


def build_prompt(detail: str, custom_prompt: str | None, want_json: bool) -> str:
    if custom_prompt:
        base = custom_prompt
    else:
        base = DEFAULT_PROMPT_TEMPLATE.format(length_guidance=DETAIL_GUIDANCE[detail])
    if want_json:
        base = base + JSON_SCHEMA_HINT
    return base


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("url")
@click.option(
    "--detail",
    type=click.Choice(["short", "medium", "long"], case_sensitive=False),
    default="medium",
    show_default=True,
    help="Summary length / depth.",
)
@click.option(
    "--prompt",
    "prompt_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to a custom prompt file. Replaces the default prompt entirely.",
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Gemini model identifier.",
)
@click.option(
    "--json",
    "want_json",
    is_flag=True,
    help="Return a structured JSON object (title, summary_md, key_points, entities).",
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the result to this file instead of stdout.",
)
@click.option("-v", "--verbose", is_flag=True, help="Print progress to stderr.")
def main(
    url: str,
    detail: str,
    prompt_file: Path | None,
    model: str,
    want_json: bool,
    output_file: Path | None,
    verbose: bool,
) -> None:
    """Summarize a YouTube video. Pass the video URL as the first argument."""

    def log(msg: str) -> None:
        if verbose:
            click.echo(msg, err=True)

    api_key = resolve_api_key()
    custom_prompt = prompt_file.read_text() if prompt_file else None
    prompt = build_prompt(detail, custom_prompt, want_json)

    with tempfile.TemporaryDirectory(prefix="yt-summary-") as tmp:
        tmp_dir = Path(tmp)
        log(f"→ downloading audio for {url}")
        audio_path, info = download_audio(url, tmp_dir)
        log(f"  audio: {audio_path.name}  duration={info.get('duration')}s  "
            f"size={audio_path.stat().st_size / 1_048_576:.1f}MB")

        client = genai.Client(api_key=api_key)
        log(f"→ uploading to Gemini Files API")
        uploaded = client.files.upload(file=str(audio_path))
        try:
            uploaded = wait_for_file_active(client, uploaded.name)
            log(f"→ analyzing with {model}")

            config_kwargs = {"temperature": 0.3}
            if want_json:
                config_kwargs["response_mime_type"] = "application/json"
            response = client.models.generate_content(
                model=model,
                contents=[uploaded, prompt],
                config=types.GenerateContentConfig(**config_kwargs),
            )
        finally:
            try:
                client.files.delete(name=uploaded.name)
            except Exception:  # noqa: BLE001
                pass

    text = response.text or ""
    if not text.strip():
        raise click.ClickException("Gemini returned an empty response")

    if want_json:
        # Validate it's parseable; pretty-print on success.
        try:
            text = json.dumps(json.loads(text), indent=2)
        except json.JSONDecodeError:
            log("  warning: response was not valid JSON; emitting raw text")

    if output_file:
        output_file.write_text(text)
        log(f"→ wrote {output_file}")
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")


if __name__ == "__main__":
    main()
