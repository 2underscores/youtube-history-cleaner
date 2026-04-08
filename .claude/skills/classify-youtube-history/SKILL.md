---
name: classify-youtube-history
description: This skill should be used when the user asks to classify, clean up, or process their YouTube watch history. Covers splitting history into chunks, classifying each video by category, collating results, and running the reconciliation report.
version: 1.0.0
---

# Classify YouTube History

Classify `scraped-data/history.json` into `scraped-data/history-classified.json` by adding `category` and `delete` fields to each item. Do NOT use any external AI API — classify by reading titles yourself.

## User Profile

The user is an AI/SWE manager. Keep anything tech, AI, software, academic, economics, or science. Delete entertainment, gaming, sports, movie/TV clips, etc.

## Workflow

### 1. Split into chunks

Chunks of 50 go into `scraped-data/tmp-work-dir/input/`. Use the existing `split_history.py` if present, or split manually:

```bash
uv run split_history.py
```

### 2. Classify each chunk

Read each `input/chunk_NN.json`, classify every item, write the result to `output/chunk_NN.json` (same directory structure). Add two fields per item:
- `"category"` — string from the category list below
- `"delete"` — `true` to delete, `false` to keep

**Always announce before starting each chunk and after finishing it.** Example:
> Processing chunk 3/12...
> Chunk 3 done. Moving to chunk 4.

Never use `python` or `python3` directly. Always use `uv run`.

### 3. Collate outputs

After all chunks are classified:

```bash
uv run collate_history.py
```

This merges all `output/chunk_*.json` files into `scraped-data/history-classified.json`.

### 4. Reconcile

```bash
uv run reconcile_history.py
```

This prints a summary table: per-category and per-month breakdown of delete vs. keep counts.

---

## Category List

Use exactly these strings for `"category"`:

**Keep (`delete: false`):**
- `AI/Technology`
- `Software/Programming`
- `Software/Technology`
- `Software/Security`
- `Science/Academic`
- `Science/Engineering`
- `Science/Nature`
- `Science/Math`
- `Science/Health`
- `Education/Academic`
- `Education/Self-improvement`
- `Economics/Business`
- `Economics/Finance`
- `Economics/Academic`
- `News/Current Affairs`

**Delete (`delete: true`):**
- `Movie/TV Clip`
- `Gaming`
- `Gaming/Tech History`
- `Entertainment/Comedy`
- `Entertainment/Shorts`
- `Entertainment/Celebrity`
- `Entertainment/Cars`
- `Entertainment/Lifestyle`
- `Entertainment/Music`
- `Entertainment/Film`
- `Sports`
- `Food/Cooking`

**Ambiguous — use judgment (`delete` depends on content):**
- `Unknown` — delete if unclear

---

## Keep vs. Delete Rules

| Keep | Delete |
|------|--------|
| AI/ML papers, tools, frameworks | Movie/TV clips or recaps |
| Software engineering content | Sports highlights or commentary |
| Academic lectures or research | Gaming videos |
| Economics, finance, business strategy | Celebrity gossip or lifestyle |
| Science explainers | Comedy skits or entertainment |
| Tech news and product reviews | Music videos |
| Self-improvement (career/skills focused) | Cooking or food content |

---

## Important Notes

- **Never use `python` or `python3` commands** — always `uv run`
- If a JSON file has encoding issues (e.g. curly unicode quotes `\u201c` `\u201e` inside strings), escape them properly before collating
- Chunk filenames must be zero-padded: `chunk_01.json`, `chunk_02.json`, etc.
- Each output item must preserve all original fields (`title`, `url`, `video_id`, `watched_at`) and add `category` and `delete`
