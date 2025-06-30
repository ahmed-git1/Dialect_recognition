#!/usr/bin/env python3
"""
remove_dead.py

Reads:
  - arab_stations.json            (your full stations file)
  - dead_stations_with_urls.csv   (CSV with columns station_id,url for all failures)

Removes any station_id listed in the CSV from both stations_by_country
and stations_by_city, then writes out a pruned JSON.
"""

import json
import csv

# 1. Load dead IDs
dead_ids = set()
with open('dead_stations_with_urls.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        dead_ids.add(row['station_id'])
print(f"Removing {len(dead_ids)} dead station IDs from JSON...")

# 2. Load your stations JSON
with open('arab_stations.json', encoding='utf-8') as f:
    data = json.load(f)

# 3. Prune each block
for block_key in ('stations_by_country', 'stations_by_city'):
    block = data.get(block_key, {})
    for group, stations in block.items():
        removed = 0
        for sid in list(stations):
            if sid in dead_ids:
                del stations[sid]
                removed += 1
        if removed:
            print(f"  - {removed} removed from {block_key}['{group}']")

# 4. Write a new JSON file
with open('arab_stations.pruned.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Pruned JSON saved to arab_stations.pruned.json")
