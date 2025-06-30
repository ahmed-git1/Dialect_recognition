#!/usr/bin/env python3
"""
repair_dead.py

Automatically repair dead streams listed in dead_stations_with_urls.csv using:
 1) RadioBrowser (via pyradios) for fresh lookup
 2) fallback to WorldRadioMap scraping for unresolved cases
"""
import csv
from pyradios import RadioBrowser
from arabic_radio_recorder import verify_stream_url, fetch_worldradiomap_stations


def lookup_radiobrowser(name, country):
    """Synchronously search RadioBrowser for a station."""
    try:
        rb = RadioBrowser()
        results = rb.search(name=name, limit=10)
        if country:
            country_lower = country.lower()
            results = [r for r in results if r.get('countrycode','').lower() == country_lower]
        if results:
            return results[0].get('url')
    except Exception:
        pass
    return None


def parse_station_id(sid):
    """Parse station_id into (search_name, country, city)."""
    parts = sid.split('-')
    if not parts:
        return sid, None, None
    country = parts[-1]
    city = parts[-2] if len(parts) >= 3 else None
    # join all except country as name
    name = ' '.join(parts[:-1])
    return name, country, city


def write_missing(missing_ids):
    """Write out IDs that couldn’t be auto-repaired for manual review."""
    with open('still_missing.txt', 'w', encoding='utf-8') as f:
        for sid in missing_ids:
            f.write(sid + '\n')
    print("Wrote {} station IDs to still_missing.txt for manual review.".format(len(missing_ids)))


def main():
    # Load dead stations
    dead = []
    try:
        with open('dead_stations_with_urls.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                sid = row.get('station_id')
                url = row.get('url')
                if sid and url:
                    dead.append((sid, url))
    except FileNotFoundError:
        print("Error: dead_stations_with_urls.csv not found.")
        return

    repairs = []
    missing = []

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
                    if sid in stations:
                        alt = stations[sid]
                        if verify_stream_url(alt):
                            print(f"✓ {sid}: WorldRadioMap → {alt}")
                            new_url = alt
                        else:
                            print(f"✗ {sid}: WRM URL failed verification")
                    else:
                        print(f"✗ {sid}: no matching station on WorldRadioMap for {city}")
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
