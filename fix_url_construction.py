#!/usr/bin/env python3
"""
Fix URL construction issues in arab_stations.json
The problem is that relative paths like "../sa/play/sba_saudia.htm" are being used directly
instead of being resolved to proper absolute URLs.
"""

import json
import re
from urllib.parse import urljoin, urlparse

def fix_relative_urls(data):
    """
    Fix relative URLs in the stations data by converting them to absolute URLs.
    """
    base_url = "https://worldradiomap.com/"
    fixed_count = 0
    
    # Fix stations_by_country
    for country_code, stations in data.get('stations_by_country', {}).items():
        for station_id, url in stations.items():
            if url.startswith('../'):
                # Convert relative path to absolute URL
                absolute_url = urljoin(base_url, url)
                stations[station_id] = absolute_url
                fixed_count += 1
                print(f"Fixed country station {station_id}: {url} -> {absolute_url}")
    
    # Fix stations_by_city
    for city, stations in data.get('stations_by_city', {}).items():
        for station_id, url in stations.items():
            if url.startswith('../'):
                # Convert relative path to absolute URL
                absolute_url = urljoin(base_url, url)
                stations[station_id] = absolute_url
                fixed_count += 1
                print(f"Fixed city station {station_id}: {url} -> {absolute_url}")
    
    return fixed_count

def main():
    # Load the original JSON file
    try:
        with open('arab_stations.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: arab_stations.json not found!")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return
    
    print("Fixing relative URLs in arab_stations.json...")
    fixed_count = fix_relative_urls(data)
    
    if fixed_count > 0:
        # Save the fixed data
        with open('arab_stations_fixed.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\nFixed {fixed_count} URLs")
        print("Fixed data saved to arab_stations_fixed.json")
        print("\nTo use the fixed data, either:")
        print("1. Replace the original file: mv arab_stations_fixed.json arab_stations.json")
        print("2. Or update your code to use arab_stations_fixed.json")
    else:
        print("No relative URLs found to fix.")

if __name__ == "__main__":
    main() 