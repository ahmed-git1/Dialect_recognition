#!/usr/bin/env python3
import json
import re

# Load the JSON file
def load_json(path='arab_stations.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def is_valid_city_name(city):
    # List of invalid words that might be mistaken for cities
    invalid_words = {
        'fm', 'radio', 'hits', 'news', 'live', 'stream', 'play', 'channel',
        'station', 'broadcast', 'music', 'sport', 'sports', 'talk', 'classic',
        'gold', 'silver', 'platinum', 'hit', 'top', 'best', 'local', 'national',
        'international', 'world', 'arab', 'arabic', 'english', 'french'
    }
    
    # Check if the city name is valid
    if not city or not city.strip():
        return False
    
    # Convert to lowercase for comparison
    city_lower = city.lower()
    
    # Check if it's in the invalid words list
    if city_lower in invalid_words:
        return False
    
    # Check if it's not just special characters or numbers
    if re.match(r'^[^a-zA-Z\u0600-\u06FF]+$', city):
        return False
    
    # Check if it's not a country code (usually 2 letters)
    if len(city) == 2 and city.isupper():
        return False
    
    # Check if it's not just a single word that's too short
    if len(city) < 3:
        return False
    
    return True

def get_cities_from_json(data):
    cities = set()
    
    # Get cities from stations_by_city section
    if 'stations_by_city' in data:
        for city in data['stations_by_city'].keys():
            if is_valid_city_name(city):
                cities.add(city.lower())
    
    # Get cities from stations_by_country section
    for country, stations in data.get('stations_by_country', {}).items():
        for station_id in stations.keys():
            # Try to extract city from station ID (e.g., quran-radio-makkah-SA)
            parts = station_id.split('-')
            if len(parts) >= 3:
                # The city is usually the second-to-last part before the country code
                city = parts[-2].lower()
                if is_valid_city_name(city):
                    cities.add(city)
    
    return sorted(cities)

def main():
    try:
        data = load_json()
        cities = get_cities_from_json(data)
        
        print("Cities found in arab_stations.json:")
        for city in cities:
            print(f"- {city}")
        print(f"\nTotal: {len(cities)} cities")
        
        # Print some statistics
        print("\nStatistics:")
        print(f"Number of cities from stations_by_city: {len(data.get('stations_by_city', {}))}")
        print(f"Number of countries: {len(data.get('stations_by_country', {}))}")
        
    except Exception as e:
        print(f"Error processing JSON file: {e}")

if __name__ == "__main__":
    main() 