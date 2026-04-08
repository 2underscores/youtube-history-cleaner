# CLAUDE.md

See README.md for full project details. This is a YouTube history cleaner — it fetches, classifies, and deletes YouTube watch history.

## Your job

Help the user walk through the steps in order. At the start of each session, figure out where they are and guide them to the next step.

### The steps

1. **Fetch history** — `uv run main.py` → produces `scraped-data/history.json`
2. **Classify** — user says "Classify my YouTube history" → you run the `/classify-youtube-history` skill
3. **Review (optional)** — `uv run reconcile_history.py` → prints keep/delete breakdown by category and month
4. **Delete** — `uv run main.py --delete` → permanently deletes everything marked `delete: true`

### How to orient at session start

Check what files exist in `scraped-data/` to determine progress:
- No `history.json` → start at Step 1
- `history.json` exists, no `history-classified.json` → start at Step 2
- `history-classified.json` exists → offer Step 3 (review) and Step 4 (delete)

Then tell the user where they are and ask if they want to continue.

### Important notes

- Chrome must be open and signed into Google for fetch and delete steps
- Deletion is permanent — always offer the reconciliation report (Step 3) before Step 4
- The classify skill can be customised: `.claude/skills/classify-youtube-history/SKILL.md` has the user profile and categories
