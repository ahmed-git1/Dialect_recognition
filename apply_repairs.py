#!/usr/bin/env python3
import json
import csv

# Load your original JSON
with open('arab_stations.json', encoding='utf-8') as f:
    data = json.load(f)

# Read dead_repairs.csv
with open('dead_repairs.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    repairs = {row['station_id']: row['new_url'] for row in reader}

# Helper to update a dict in place
def update_block(block):
    for sid in list(block):
        if sid in repairs:
            block[sid] = repairs[sid]

# Update both country & city blocks
for country_code, block in data.get('stations_by_country', {}).items():
    update_block(block)
for city, block in data.get('stations_by_city', {}).items():
    update_block(block)

# Write back to a new file (to be safe)
with open('arab_stations.fixed.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Applied {len(repairs)} auto-repairs; output → arab_stations.fixed.json")
