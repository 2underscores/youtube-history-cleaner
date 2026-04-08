# YouTube History Cleaner

Scrape your YouTube watch history, classify each video as productive or not using Claude, then bulk-delete the noise so your YouTube homepage only recommends content you actually want to see.

No YouTube API key required — it reads your Chrome session cookies and talks directly to Google's internal activity API.

## How it works

1. **Fetch** — scrapes your full YouTube watch history from `myactivity.google.com` using your Chrome cookies
2. **Classify** — uses Claude Code (AI) to label each video by category and mark it for deletion or keeping, based on your profile
3. **Delete** — re-fetches history to get activity IDs, then bulk-deletes everything marked for removal via Google's activity API

## Customisation
The default profile keeps **tech, AI, software, science, and economics** content and deletes **entertainment, gaming, sports, movie/TV clips**, etc. Edit the profile in the "User Profile & Categories" section of `.claude/skills/classify-youtube-history/SKILL.md` to match your own preferences.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Claude Code](https://claude.ai/code) — for the classify step
- Chrome browser signed into your Google/YouTube account

## Setup

```bash
git clone https://github.com/your-username/youtube-history-cleaner
cd youtube-history-cleaner
uv sync
```

## Usage

### Step 1 — Fetch your history

```bash
uv run main.py
```

Paginates through all your YouTube watch history and saves it to `scraped-data/history.json`. Deduplicates by video ID, keeping the most recent watch.

### Step 2 — Classify with Claude

Open Claude Code in this directory and run:

```
/classify-youtube-history
```

This Claude Code skill will:
- Split `history.json` into chunks of 50
- Classify each video by category and mark it `delete: true/false`
- Collate the results into `scraped-data/history-classified.json`

### Step 2.5 (optional) — Review the classification report

```bash
uv run reconcile_history.py
```

Prints a breakdown of videos by category and month — keep vs. delete counts — so you can sanity-check before deleting anything.

### Step 3 — Delete

```bash
uv run main.py --delete
```

Fetches fresh activity IDs from Google, matches them against `history-classified.json`, and deletes everything marked `delete: true`. Prints each deletion as it goes.

### Step 4 — Enjoy

Log into YouTube. Your home feed will now only train on the videos you kept.

## Project structure

```
main.py                  # fetch history + delete marked videos
split_history.py         # splits history.json into chunks for classification
collate_history.py       # merges classified chunks into history-classified.json
reconcile_history.py     # prints category/month summary report
scraped-data/
  history.json           # raw scraped history (with activity_id)
  history-classified.json  # classified history with category + delete fields
.claude/skills/
  classify-youtube-history/  # Claude Code skill for classification
```

## Notes

- The fetch step reads Chrome's cookie store directly — make sure Chrome is open and you're signed into Google
- The delete step re-fetches history each run to get fresh activity IDs.
- Deletion is permanent — review the reconciliation report before running `--delete`
- If you have a very large history, the classify step will take a few minutes as Claude works through the chunks
