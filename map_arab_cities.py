#!/usr/bin/env python3
import json
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
from list_cities_from_json import load_json, get_cities_from_json
from folium.plugins import MarkerCluster

def get_city_coordinates(city, country_code=None):
    """Get coordinates for a city using geopy."""
    geolocator = Nominatim(user_agent="arab_radio_mapper")
    try:
        # Add country code to improve accuracy
        query = f"{city}, {country_code}" if country_code else city
        location = geolocator.geocode(query)
        if location:
            return (location.latitude, location.longitude)
    except GeocoderTimedOut:
        time.sleep(1)  # Wait before retrying
        return get_city_coordinates(city, country_code)
    return None

def create_map(cities_data):
    """Create an interactive map with city markers."""
    # Create a map centered on the Middle East
    m = folium.Map(
        location=[25, 45],
        zoom_start=4,
        tiles='CartoDB positron'
    )
    
    # Add a title to the map
    title_html = '''
        <h3 align="center" style="font-size:16px">
            <b>Arabic Radio Stations Coverage Map</b>
        </h3>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Create a marker cluster
    marker_cluster = MarkerCluster().add_to(m)
    
    # Add markers for each city
    for city, coords in cities_data.items():
        if coords:
            # Create popup content with city name and country
            popup_content = f'''
                <div style="font-family: Arial, sans-serif; min-width: 200px;">
                    <h4 style="margin: 0 0 5px 0; color: #333;">{city.title()}</h4>
                    <p style="margin: 0; color: #666;">
                        <strong>Coordinates:</strong><br>
                        Lat: {coords[0]:.4f}<br>
                        Lon: {coords[1]:.4f}
                    </p>
                </div>
            '''
            
            # Create a custom icon with the city name
            icon_html = f'''
                <div style="
                    background-color: white;
                    border: 2px solid red;
                    border-radius: 50%;
                    padding: 5px;
                    text-align: center;
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                    font-weight: bold;
                    color: #333;
                    width: 100px;
                    position: relative;
                    top: -30px;
                    left: -40px;
                ">
                    {city.title()}
                </div>
            '''
            
            # Create the marker with custom icon
            folium.Marker(
                coords,
                popup=folium.Popup(popup_content, max_width=300),
                icon=folium.DivIcon(
                    html=icon_html,
                    class_name='custom-marker'
                ),
                tooltip=f"{city.title()}\n{coords[0]:.4f}, {coords[1]:.4f}"
            ).add_to(marker_cluster)
    
    # Add a legend
    legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; 
                    border:2px solid grey; z-index:9999; 
                    background-color:white;
                    padding: 10px;
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    ">
        <p><strong>Legend</strong></p>
        <p><i class="fa fa-map-marker" style="color:red"></i> Radio Station City</p>
        <p style="font-size: 12px; color: #666;">Click on markers to see coordinates</p>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add custom CSS
    css = '''
        <style>
            .folium-popup {
                font-family: Arial, sans-serif;
            }
            .folium-popup h4 {
                color: #333;
                margin: 0 0 5px 0;
            }
            .folium-popup p {
                color: #666;
                margin: 0;
            }
            .custom-marker {
                background: none;
                border: none;
            }
            .custom-marker div {
                text-align: center;
                white-space: nowrap;
            }
        </style>
    '''
    m.get_root().header.add_child(folium.Element(css))
    
    # Save the map
    m.save('arab_cities_map.html')

def main():
    # Load cities from JSON
    data = load_json()
    cities = get_cities_from_json(data)
    
    # Dictionary to store city coordinates
    cities_with_coords = {}
    
    # Country codes mapping for better geocoding
    country_codes = {
        'jeddah': 'SA',
        'dubai': 'AE',
        'abu-dhabi': 'AE',
        'doha': 'QA',
        'amman': 'JO',
        'baghdad': 'IQ',
        'beirut': 'LB',
        'cairo': 'EG',
        'damascus': 'SY',
        'muscat': 'OM',
        'riyadh': 'SA',
        'tunis': 'TN',
        'casablanca': 'MA',
        'alexandria': 'EG',
        'manama': 'BH',
        'kuwait': 'KW',
        'sanaa': 'YE',
        'khartoum': 'SD',
        'tripoli': 'LY',
        'algiers': 'DZ',
        'rabat': 'MA',
        'jerusalem': 'IL',
        'gaza': 'PS',
        'ramallah': 'PS',
        'najaf': 'IQ',
        'basra': 'IQ',
        'mosul': 'IQ',
        'homs': 'SY',
        'aleppo': 'SY',
        'latakia': 'SY',
        'tartus': 'SY',
        'hama': 'SY',
        'idlib': 'SY',
        'deir-ez-zor': 'SY',
        'hasakah': 'SY',
        'qamishli': 'SY',
        'kobani': 'SY'
    }
    
    print("Geocoding cities...")
    for city in cities:
        print(f"Getting coordinates for {city}...")
        country_code = country_codes.get(city.lower())
        coords = get_city_coordinates(city, country_code)
        if coords:
            cities_with_coords[city] = coords
            print(f"Found coordinates for {city}: {coords}")
        else:
            print(f"Could not find coordinates for {city}")
        time.sleep(1)  # Be nice to the geocoding service
    
    print("\nCreating map...")
    create_map(cities_with_coords)
    print("Map has been saved as 'arab_cities_map.html'")

if __name__ == "__main__":
    main() 