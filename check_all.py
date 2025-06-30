#!/usr/bin/env python3
import json
import csv
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

def verify_stream_url(url, timeout=5):
    """Return True if the stream URL responds, False otherwise."""
    try:
        parsed = urlparse(url)
        if parsed.scheme in ('http', 'https'):
            headers = {'User-Agent': 'Mozilla/5.0'}
            if url.endswith(('.m3u8', '.m3u', '.pls')):
                resp = requests.head(url, timeout=timeout, headers=headers)
                return resp.status_code == 200
            resp = requests.get(url, headers=headers, stream=True, timeout=timeout)
            if resp.status_code == 200:
                for chunk in resp.iter_content(1024):
                    if chunk:
                        return True
                    break
            return False
        return True
    except Exception:
        return False

# 1. Load your stations JSON
with open('arab_stations.json', encoding='utf-8') as f:
    data = json.load(f)

# 2. Flatten all station_id → url mappings
stations = {}
for country_map in data.get('stations_by_country', {}).values():
    stations.update(country_map)
for city_map in data.get('stations_by_city', {}).values():
    stations.update(city_map)

print(f"Total stations to check: {len(stations)}")

# 3. Verify in parallel
def check(item):
    sid, url = item
    result = verify_stream_url(url, timeout=5)
    return sid, url, result

with ThreadPoolExecutor(max_workers=20) as pool:
    results = list(pool.map(check, stations.items()))

# 4. Write dead ones to CSV
dead = [(sid, url) for sid, url, ok in results if not ok]

with open('dead_stations_with_urls.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['station_id', 'url'])
    writer.writerows(dead)

print(f"✅ Checked {len(stations)} stations: {len(dead)} dead.")
print("🔗 See dead_stations_with_urls.csv for the full list.")
