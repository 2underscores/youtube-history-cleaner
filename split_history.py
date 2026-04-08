"""Split history.json into chunks of 50 for classification."""
import json
import os

CHUNK_SIZE = 50
INPUT = "scraped-data/history.json"
OUTPUT_DIR = "scraped-data/tmp-work-dir/input"

with open(INPUT) as f:
    history = json.load(f)

os.makedirs(OUTPUT_DIR, exist_ok=True)

total = len(history)
num_chunks = (total + CHUNK_SIZE - 1) // CHUNK_SIZE

for i in range(num_chunks):
    chunk = history[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE]
    out_path = os.path.join(OUTPUT_DIR, f"chunk_{i+1:02d}.json")
    with open(out_path, "w") as f:
        json.dump(chunk, f, indent=2)
    print(f"Wrote chunk {i+1}/{num_chunks} ({len(chunk)} items) -> {out_path}")

print(f"\nTotal: {total} items split into {num_chunks} chunks.")
