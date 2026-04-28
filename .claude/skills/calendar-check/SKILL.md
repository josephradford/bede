---
name: calendar-check
description: >
  Check all Google Calendars for events, not just the primary. Use this skill
  whenever you need to look up calendar events, check for conflicts, or list
  what's on a given day/range.
---

# Calendar Check Skill

Google Calendar lookups must check ALL calendars, not just the primary.
Joe has multiple calendars (personal, work, birthdays, shared, etc.) and
events on secondary calendars are frequently missed.

## Steps

1. Call `list_calendars` via workspace-mcp to get every calendar shared with
   the account.

2. For EACH calendar ID returned, call `get_events` with the requested date
   range.

3. Merge all results into a single list, sorted chronologically. Include the
   calendar name with each event so they're distinguishable:
   - `[Personal] Dinner with friends — 18:00`
   - `[Birthdays] Sarah's Birthday`
   - `[Work] Team standup — 09:30`

4. Return the merged list.

## Rules

- Never skip a calendar — even if the name looks irrelevant, it may contain
  events Joe cares about
- If a calendar API call fails, note which calendar failed and continue with
  the others — don't abort the whole check
- For conflict checking, flag any overlapping events across all calendars
- The Google account is `ai.joeradford@gmail.com` — always use this email
