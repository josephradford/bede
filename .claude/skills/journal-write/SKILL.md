---
name: journal-write
description: >
  Write a daily journal entry to /vault/Journal/YYYY-MM-DD.md. Use this skill
  when writing or updating journal entries, including from the evening
  reflection. Handles the template, formatting, priorities preservation, and
  tomorrow's file.
---

# Journal Write Skill

Write a structured daily journal entry from collected data and analysis.

ARGUMENTS: the skill receives the date (YYYY-MM-DD) and the analysis content
to write. If no arguments, use today's date.

## Step 1 — Read inputs

- Read `/vault/Bede/journal-template.md` for the canonical structure
- Read `/vault/Bede/reflection-memory.md` for formatting corrections and
  preferences from past reflections — these override defaults
- Read `/vault/Journal/[date].md` if it exists — check for an existing
  `## Priorities` section to preserve

## Step 2 — Build the journal file

Follow the template structure exactly:

```markdown
---
date: YYYY-MM-DD
author: bede
type: journal
tags:
  - daily
---

# YYYY-MM-DD

## Priorities
[preserve from existing file if present, otherwise from analysis]

## Timeline
*Generated HH:MM*

### Weather
[conditions, high/low, precipitation, wind]

[chronological reconstruction from all data sources]
- **~HH:MM** — [event/activity] *(source)*

## Analysis

### Health
### Work
### Family
### Screen Time
### Safari
### YouTube
### Professional Development
### Wellbeing

## Priorities Check
- ✓/✗/~/? [priority] — [evidence]

> [one honest paragraph — Bede's assessment in second person]

## Tomorrow's Priorities
- [suggested priorities based on schedule and goals]
```

## Step 3 — Quality checks before writing

- **Timeline is the backbone.** It must be built from actual data, not
  summaries. Include approximate times, source attribution, and location
  transitions. Collapse quiet periods but don't skip them.
- **Screen Time, Safari, YouTube must be critical.** Flag mindless consumption
  directly. Don't soften or hedge. "You spent 2 hours on Reddit" not "there
  was some browsing activity."
- **Priorities Check needs evidence.** Each priority gets a symbol (✓/✗/~/?)
  with a one-line justification referencing actual data (workout logs, location,
  screen time, calendar).
- **The honest paragraph** is Bede's voice in second person. It should name
  the gap between intention and behaviour, or acknowledge when the day went
  well. Don't be vague or generic.
- **Every section must have content or "data unavailable".** Never silently
  skip a section.

## Step 4 — Write the journal

Write to `/vault/Journal/[date].md`. If the file exists and has a
`## Priorities` section, preserve that section and replace everything else.

## Step 5 — Write tomorrow's priorities

Calculate tomorrow's date. Create or update `/vault/Journal/[tomorrow].md`:

```markdown
# [tomorrow's date]

## Priorities
- [each suggested priority]
```

If tomorrow's file already exists, only add/update the `## Priorities`
section — do not overwrite other content.

## Step 6 — Commit and push

Use `/vault-write` or directly:
```bash
cd /vault && git add -A && git commit -m "journal: [date] evening reflection" && git push
```

## Common mistakes (from reflection-memory.md)

Read `/vault/Bede/reflection-memory.md` each time — it contains corrections
Joe has given about past journal entries. These override any defaults above.
Typical issues include:
- Incorrect categorisation of screen time (e.g. calling productive time
  "mindless")
- Missing data sources that were available but not queried
- Overly generous or overly harsh assessments
- Wrong time attributions in the timeline
