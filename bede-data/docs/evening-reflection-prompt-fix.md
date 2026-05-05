# Evening Reflection Prompt Fix

## Problem

The current task prompt for the evening reflection is:

> Write the evening reflection journal entry.

This is too vague. The LLM sometimes skips calling `get_location_summary` and other tools, resulting in incomplete journal entries that lack timeline, location, and wellbeing data expected by the journal template.

## Suggested New Prompt

Replace the `prompt` field in the `schedules` table for the evening reflection task with:

```
Write the evening reflection journal entry. You MUST call the following tools before writing:

1. get_location_summary - for the Timeline section (places visited today)
2. get_wellbeing - for the State of Mind data
3. get_safari_history - for notable browsing activity
4. get_screen_time - for screen time summary

Do not skip any of these calls. The journal template at /vault/Bede/journal-template.md defines the expected structure. Every section that has a corresponding tool MUST be populated with real data from that tool, never omitted or summarised as "nothing notable".
```

## How to Apply

Update the schedule via the bede-data API:

```bash
curl -X PATCH "https://bede-data.DOMAIN/api/config/schedules/<schedule_id>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write the evening reflection journal entry. You MUST call the following tools before writing:\n\n1. get_location_summary - for the Timeline section (places visited today)\n2. get_wellbeing - for the State of Mind data\n3. get_safari_history - for notable browsing activity\n4. get_screen_time - for screen time summary\n\nDo not skip any of these calls. The journal template at /vault/Bede/journal-template.md defines the expected structure. Every section that has a corresponding tool MUST be populated with real data from that tool, never omitted or summarised as \"nothing notable\"."}'
```

Alternatively, update directly on the server:

```bash
sqlite3 /data/sqlite/bede.db "UPDATE schedules SET prompt = 'Write the evening reflection journal entry. You MUST call the following tools before writing:

1. get_location_summary - for the Timeline section (places visited today)
2. get_wellbeing - for the State of Mind data
3. get_safari_history - for notable browsing activity
4. get_screen_time - for screen time summary

Do not skip any of these calls. The journal template at /vault/Bede/journal-template.md defines the expected structure. Every section that has a corresponding tool MUST be populated with real data from that tool, never omitted or summarised as \"nothing notable\".' WHERE name = 'evening-reflection';"
```
