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
The date and analysis content come from the conversation context (e.g. the
evening reflection passes its gathered data and analysis here).

## Step 1 — Read inputs

- Read `/vault/Bede/journal-template.md` for the canonical structure — follow
  it exactly
- Read `/vault/Bede/reflection-memory.md` for corrections and preferences
  from past reflections — these override the template defaults and the
  quality checks below
- Read `/vault/Journal/[date].md` if it exists — check for an existing
  `## Priorities` section to preserve

## Step 2 — Quality checks before writing

Apply these checks to the analysis content before writing the journal:

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

## Step 3 — Write the journal

Write to `/vault/Journal/[date].md` following the structure from
`journal-template.md`. If the file exists and has a `## Priorities` section,
preserve that section and replace everything else.

## Step 4 — Write tomorrow's priorities

Calculate tomorrow's date. Create or update `/vault/Journal/[tomorrow].md`
with a `## Priorities` section containing the suggested priorities.

If tomorrow's file already exists, only add/update the `## Priorities`
section — do not overwrite other content.

## Step 5 — Commit and push

Use /vault-write to commit both files with message
`journal: [date] evening reflection`.
