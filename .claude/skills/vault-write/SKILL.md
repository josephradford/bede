---
name: vault-write
description: >
  Write a file to the Obsidian vault and commit + push to git. Use this
  skill ANY time you write or modify a file under /vault/ to ensure changes
  are persisted and synced.
---

# Vault Write Skill

Every vault write must be followed by a git commit and push. This skill
ensures nothing is lost.

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

## Rules

- Always commit immediately after writing — never leave uncommitted changes
- If the push fails (e.g. conflict), run `git pull --rebase && git push`
- If multiple files are written as part of one logical operation, commit them
  together in a single commit
- Never force push
