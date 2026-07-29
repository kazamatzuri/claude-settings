---
name: ste-writing
description: Rewrite prose (docs, READMEs, PR descriptions, Linear tickets, runbooks, error messages, release notes, comments — never code) into ASD-STE100 Simplified Technical English to remove "AI slop". Use when asked to make writing not sound like AI, make docs clear or plain, enforce a controlled writing style, or write technical documentation that reads human. Two modes — strict (procedures/safety) and STE-flavored (general prose).
---

# ste-writing

Write prose in ASD-STE100 Simplified Technical English. Apply it to documentation, READMEs, pull-request bodies, Linear tickets, runbooks, error messages, release notes, and comments. Do not apply it to code, identifiers, or command syntax. Do not apply it to marketing copy, essays, or anything that needs a voice. STE strips voice on purpose.

## Rules

WORDS
- Use one name for one thing. Do not call the same item by two different names.
- Use the short common word: start (not begin/commence/initiate), use (not utilize/leverage), help (not facilitate), make sure (not ensure), before (not prior to), after (not subsequent to), about (not regarding/concerning), get (not obtain/acquire), show (not demonstrate), also (not additionally/furthermore/moreover).
- Give each word one meaning. "fall" means to move down, not to decrease.
- No marketing adjectives: seamless, robust, powerful, cutting-edge, effortless, world-class, next-generation, revolutionary.
- American spelling.

VERBS
- Active voice. "the parser reads the file", not "the file is read by the parser".
- Use a verb for an action. "analyze the log", not "perform an analysis of the log".
- No stacked auxiliaries. Not "it is important to note that this may help to improve". Write "this improves X".
- No "-ing" main verb where a simple tense works.
- No phrasal verbs where a plain verb exists: start (not spin up), delete (not tear down), check (not look into).

SENTENCES
- One instruction per sentence. Max 20 words (instruction), max 25 (descriptive).
- No contractions. Use articles: a, an, the, this, these.

PUNCTUATION
- No semicolons. Write two sentences.
- No em dashes. Use a period, a comma, or parentheses. (STE itself does not ban the em dash. This skill does, because it is an AI tell.)

STRUCTURE
- One topic per paragraph, max six sentences. For steps, use a numbered vertical list, one action per item, imperative form. Put a condition before its command.
- No time estimates.

Write only the requested text. No preamble, no summary, no closing remarks.

## Modes

- **strict** — procedures, runbooks, incident notes, safety text, error messages: apply every rule and both length caps.
- **STE-flavored** (default) — general prose (READMEs, PR bodies, Linear tickets, docs): apply the sentence, paragraph, active-voice, and no-phrasal-verb discipline. Relax the ~900-word vocabulary lockdown so the text keeps enough range to read naturally.

## Self-lint (run before returning text)

1. Any sentence over 20 words? Split it.
2. Any semicolon or em dash? Replace it.
3. Any contraction? Expand it.
4. Any passive voice with a known actor? Make it active.
5. Any "-ing" main verb, nominalization ("perform an analysis"), or phrasal verb ("spin up")? Replace with a plain verb.
6. Same thing named two ways? Pick one name.

The rules above are mechanical and lintable. They remove the FORM of slop. Full STE also needs human judgment (the right technical noun, whether a sentence makes good sense). A checker cannot certify that, and this skill cannot make a hollow paragraph true.

## Related skills

- `anti-ai-tropes` and `humanizer` detect AI tells in existing text. They diagnose.
- This skill prescribes a writing standard. Use it to write or rewrite. Use the other two to audit the result.

Free official standard (do not paste it in full, it is copyrighted): https://asd-ste100.org

Adapted from Woosal's ste-writing skill: https://github.com/woosal1337/blog/blob/main/videos/ep01-the-cure-for-ai-slop/ste-writing-skill.md
