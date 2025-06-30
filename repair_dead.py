#!/usr/bin/env python3
"""
repair_dead.py

Automatically repair dead streams listed in dead_stations_with_urls.csv using:
 1) RadioBrowser (via pyradios) for fresh lookup
 2) fallback to WorldRadioMap scraping for unresolved cases
"""
import csv
import json
from pyradios import RadioBrowser
from arabic_radio_recorder import verify_stream_url, fetch_worldradiomap_stations


def lookup_radiobrowser(name: str, country: str) -> str | None:
    """Synchronously search RadioBrowser for a station."""
    try:
        rb = RadioBrowser()
        results = rb.search(name=name, limit=10)
        if country:
            country = country.lower()
            results = [r for r in results if r.get('countrycode','').lower() == country]
        if results:
            return results[0]['url']
    except Exception:
        pass
    return None


def parse_station_id(sid: str) -> tuple[str, str, str | None]:
    """Parse station_id into (search_name, country, city)."""
    parts = sid.split('-')
    country = parts[-1]
    city = parts[-2] if len(parts) >= 3 else None
    name = " ".join(parts[:-1]).replace('-', ' ')
    return name, country.lower(), city.lower() if city else None


def write_missing(missing_ids: list[str]) -> None:
    """Write out IDs that couldn’t be auto-repaired for manual review."""
    with open('still_missing.txt', 'w', encoding='utf-8') as f:
        for sid in missing_ids:
            f.write(sid + '\n')
    print(f"Wrote {len(missing_ids)} station IDs to still_missing.txt for manual review.")


def main():
    # Load dead stations
    dead = []
    with open('dead_stations_with_urls.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dead.append((row['station_id'], row['url']))

    repairs: list[tuple[str, str, str]] = []
    missing: list[str] = []

    print(f"Attempting to repair {len(dead)} dead streams...\n")

    for sid, old_url in dead:
        name, country, city = parse_station_id(sid)
        new_url = None
        # 1) Try RadioBrowser lookup
        candidate = lookup_radiobrowser(name, country)
        if candidate and verify_stream_url(candidate):
            print(f"✓ {sid}: RadioBrowser → {candidate}")
            new_url = candidate
        else:
            # 2) Fallback: WorldRadioMap scrape (if city known)
            if city:
                try:
                    stations = fetch_worldradiomap_stations(country, city, get_direct_urls=True)
                    if sid in stations and verify_stream_url(stations[sid]):
                        print(f"✓ {sid}: WorldRadioMap → {stations[sid]}")
                        new_url = stations[sid]
                    else:
                        print(f"✗ {sid}: no matching station on WorldRadioMap")
                except Exception as e:
                    print(f"✗ {sid}: WRM lookup failed ({e})")
        # Record outcome
        if new_url:
            repairs.append((sid, old_url, new_url))
        else:
            missing.append(sid)

    # Write out repaired entries
    with open('dead_repairs.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['station_id', 'old_url', 'new_url'])
        writer.writerows(repairs)

    print(f"\nWrote {len(repairs)} entries to dead_repairs.csv.")
    if missing:
        print("Still missing replacements for:")
        for sid in missing:
            print(f" - {sid}")
        write_missing(missing)


if __name__ == '__main__':
    main()
