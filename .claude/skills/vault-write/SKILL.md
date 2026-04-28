---
name: vault-write
description: >
  Write a file to the Obsidian vault and commit + push to git. Use this
  skill ANY time you write or modify a file under /vault/ to ensure changes
  are persisted and synced. This includes journal entries, reflection memory,
  scout memory, preference files, and any other vault content.
---

# Vault Write Skill

The vault on the server is a git clone that pulls on every task execution.
Any file written but not committed and pushed is invisible to Bede until the
next git push — there is no other sync mechanism. This is why every write
must be followed by a commit.

## Steps

1. Write or modify the file(s) under `/vault/`.
2. Stage, commit, and push:

```bash
cd /vault && git add -A && git commit -m "<short description>" && git push
```

The commit message should be short and descriptive:
- `journal: 2026-04-28 evening reflection`
- `bede: update reflection memory`
- `bede: scout memory 2026-04-28`
- `vault: update event preferences`

## Error handling

- **Push conflict:** run `git pull --rebase && git push`
- **Dirty index from previous failed commit:** run `git reset` then re-stage
  and commit cleanly
- **Auth failure:** report the error to the user — do not retry silently
- **No .git directory:** report that the vault is not a git repo — something
  is wrong with the container setup

## Rules

- Always commit immediately after writing — never leave uncommitted changes
- If multiple files are written as part of one logical operation, commit them
  together in a single commit
- Never force push
