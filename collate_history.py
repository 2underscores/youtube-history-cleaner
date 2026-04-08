"""Collate classified chunks back into history-classified.json."""
import json
import os
import glob
from collections import Counter

INPUT_DIR = "scraped-data/tmp-work-dir/output"
ORIGINAL = "scraped-data/history.json"
OUTPUT = "scraped-data/history-classified.json"

# Load original history for lookup
with open(ORIGINAL) as f:
    history = json.load(f)

# Build a map of video_id -> original item
orig_map = {item["video_id"]: item for item in history}

# Load all classified chunks
classified_files = sorted(glob.glob(os.path.join(INPUT_DIR, "chunk_*.json")))
if not classified_files:
    print("No classified chunks found in", INPUT_DIR)
    exit(1)

classified_map = {}
for path in classified_files:
    with open(path) as f:
        chunk = json.load(f)
    for item in chunk:
        classified_map[item["video_id"]] = item
    print(f"Loaded {len(chunk)} items from {path}")

# Merge: preserve original order, add category/delete fields
result = []
missing = []
for item in history:
    vid_id = item["video_id"]
    if vid_id in classified_map:
        c = classified_map[vid_id]
        result.append({**item, "category": c["category"], "delete": c["delete"]})
    else:
        missing.append(vid_id)
        result.append({**item, "category": "other", "delete": False})

with open(OUTPUT, "w") as f:
    json.dump(result, f, indent=2)

cats = Counter(item["category"] for item in result)
to_delete = sum(1 for item in result if item["delete"])

print(f"\nDone! {len(result)} items -> {OUTPUT}")
print(f"To delete: {to_delete} | To keep: {len(result) - to_delete}")
if missing:
    print(f"Missing classifications (defaulted to keep): {len(missing)}")
print("\nBy category:")
for cat, count in cats.most_common():
    print(f"  {cat}: {count}")
