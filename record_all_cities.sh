#!/usr/bin/env bash
set -e

# 1. Grab the city names into a whitespace-separated list
city_list=$(
  python arabic_radio_recorder.py \
    --import arab_stations.json \
    --list-cities \
  | sed -n 's/  - \([^(]*\) (.*/\1/p'
)

# 2. Create top‐level recordings folder
mkdir -p recordings

# 3. Loop over each city and record 30-second clips
for city in $city_list; do
  echo "=== Recording all stations in: $city (30 s each) ==="
  mkdir -p "recordings/$city"
  python arabic_radio_recorder.py \
    --import arab_stations.json \
    --city "$city" \
    --verify \
    --duration 30 \
    --output "recordings/$city"
done
