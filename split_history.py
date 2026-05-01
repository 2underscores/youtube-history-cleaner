"""Split history.json into chunks of 50 for classification."""
import json
import os
import argparse
from datetime import datetime, timezone

CHUNK_SIZE = 50
INPUT = "scraped-data/history.json"
OUTPUT_DIR = "scraped-data/tmp-work-dir/input"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--since",
    help="Only include videos watched at or after this date/timestamp "
         "(ISO 8601, e.g. 2026-04-25 or 2026-04-25T00:00:00+00:00). "
         "Omit to process all history.",
)
args = parser.parse_args()

with open(INPUT) as f:
    history = json.load(f)

if args.since:
    since_dt = datetime.fromisoformat(args.since)
    if since_dt.tzinfo is None:
        since_dt = since_dt.replace(tzinfo=timezone.utc)
    history = [
        item for item in history
        if item.get("watched_at")
        and datetime.fromisoformat(item["watched_at"]) >= since_dt
    ]
    print(f"Filtered to {len(history)} items watched since {args.since}")

os.makedirs(OUTPUT_DIR, exist_ok=True)

total = len(history)
num_chunks = (total + CHUNK_SIZE - 1) // CHUNK_SIZE

for i in range(num_chunks):
    chunk = [{"video_id": item["video_id"], "title": item["title"]} for item in history[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE]]
    out_path = os.path.join(OUTPUT_DIR, f"chunk_{i+1:02d}.json")
    with open(out_path, "w") as f:
        json.dump(chunk, f, indent=2)
    print(f"Wrote chunk {i+1}/{num_chunks} ({len(chunk)} items) -> {out_path}")

print(f"\nTotal: {total} items split into {num_chunks} chunks.")
