#!/usr/bin/env python3
# Arabic Radio Stations Recorder
# Tool to discover and record radio stations from Arab cities

import asyncio
import subprocess
import datetime
import pathlib
import os
import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from urllib.parse import urlparse
import concurrent.futures
import re
import argparse
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("radio_recorder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("arabic_radio_recorder")

def extract_direct_stream_url(play_page_url):
    """
    Extract the direct streaming URL from a WorldRadioMap play page.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        response = requests.get(play_page_url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to fetch play page: HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for audio elements first
        audio = soup.find('audio')
        if audio:
            src = audio.find('source')
            if src and src.has_attr('src'):
                return src['src']
        
        # Look for iframe sources
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            if iframe.has_attr('src'):
                src = iframe['src']
                if src.startswith('http') and any(ext in src for ext in ['.mp3', '.m3u8', '.aac', '.pls']):
                    return src
        
        # Look for links with streaming URLs
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith(('.mp3', '.m3u8', '.aac', '.pls')) or 'stream' in href or 'listen' in href:
                if href.startswith('http'):
                    return href
                else:
                    return f"https://worldradiomap.com{href}"
        
        # Look for streaming URLs in script tags
        for script in soup.find_all('script'):
            if script.string:
                # Look for various streaming URL patterns
                patterns = [
                    r'(https?://[^\s\'"]+\.(mp3|m3u8|aac|pls))',
                    r'(https?://[^\s\'"]+stream[^\s\'"]*)',
                    r'(https?://[^\s\'"]+listen[^\s\'"]*)',
                    r'(https?://[^\s\'"]+radio[^\s\'"]*)',
                    r'(https?://[^\s\'"]+live[^\s\'"]*)'
                ]
                for pattern in patterns:
                    match = re.search(pattern, script.string, re.IGNORECASE)
                    if match:
                        return match.group(1)
        
        # Look for streaming URLs in the page content
        content = response.text
        patterns = [
            r'(https?://[^\s\'"]+\.(mp3|m3u8|aac|pls))',
            r'(https?://[^\s\'"]+stream[^\s\'"]*)',
            r'(https?://[^\s\'"]+listen[^\s\'"]*)'
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    except Exception as e:
        logger.error(f"Error extracting direct stream URL from {play_page_url}: {e}")
        return None

def record_stream(url: str, seconds: int = 30, folder: str = "recordings") -> pathlib.Path:
    """
    Record a stream for the specified number of seconds using FFmpeg.
    Handles .pls and .m3u playlists, saves output as MP3.
    Also handles HTML pages by extracting the actual streaming URL.
    """
    os.makedirs(folder, exist_ok=True) # this function helps to create direc >> folder
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S") # reocrd time 
    out_file = pathlib.Path(folder) / f"radio_{ts}.mp3"

    # If it's an HTML page, extract the actual streaming URL first
    parsed = urlparse(url)
    if parsed.path.endswith('.htm') or parsed.path.endswith('.html'):
        logger.info(f"Extracting streaming URL from HTML page: {url}")
        actual_url = extract_direct_stream_url(url)
        if actual_url:
            url = actual_url
            logger.info(f"Extracted streaming URL: {url}")
            # Re-parse the URL after extraction
            parsed = urlparse(url)
        else:
            logger.error(f"Could not extract streaming URL from {url}")
            raise RuntimeError(f"Could not extract streaming URL from {url}")

    # If it's a .pls or .m3u playlist, fetch and parse it first
    if parsed.path.endswith('.pls') or parsed.path.endswith('.m3u'):
        try:
            resp = requests.get(url, timeout=10, headers={'User-Agent':'Mozilla/5.0'})
            resp.raise_for_status()
            content = resp.text
            
            # Parse PLS file
            if parsed.path.endswith('.pls'):
                for line in content.splitlines():
                    line = line.strip()
                    if line.lower().startswith('file1='):
                        candidate = line.split('=', 1)[-1].strip()
                        if candidate.lower().startswith('http'):
                            url = candidate
                            logger.info(f"Extracted streaming URL from PLS: {url}")
                            break
            
            # Parse M3U file
            elif parsed.path.endswith('.m3u'):
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith('http'):
                        url = line
                        logger.info(f"Extracted streaming URL from M3U: {url}")
                        break
                        
        except Exception as e:
            logger.warning(f"Could not parse playlist {url}: {e}")
            # leave url unchanged, ffmpeg may handle .m3u8 or fail on .pls

    # Transcode into MP3 (libmp3lame) for broad compatibility
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
        "-i", url,
        "-t", str(seconds),
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        out_file.as_posix()
    ]

    print(f"Recording {url} for {seconds} seconds...")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Successfully saved to {out_file}")
        return out_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Error recording stream {url}: {e}")
        print(f"FFmpeg error: {e.stderr}")
        raise

def verify_stream_url(url, timeout=5):
    """
    Verify if a stream URL is working by making a request.
    Returns True if the stream is accessible, False otherwise.
    """
    try:
        parsed_url = urlparse(url)
        if parsed_url.scheme in ['http', 'https']:
            headers = {
                'User-Agent': 'Mozilla/5.0'
            }
            if url.endswith(('.m3u8', '.m3u', '.pls')):
                response = requests.head(url, timeout=timeout, headers=headers)
                return response.status_code == 200
            response = requests.get(url, headers=headers, stream=True, timeout=timeout)
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        return True
                    break
            return False
        return True
    except Exception as e:
        logger.debug(f"Error verifying stream {url}: {e}")
        return False

def verify_stations_health(stations_dict, max_workers=5):
    """
    Verify the health of all stations in parallel using threads.
    Returns a dictionary of working stations.
    """
    working = {}
    total = len(stations_dict)
    print(f"Verifying {total} stations...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(verify_stream_url, url): sid for sid, url in stations_dict.items()}
        for future in concurrent.futures.as_completed(futures):
            sid = futures[future]
            ok = future.result()
            if ok:
                working[sid] = stations_dict[sid]
                print(f"✓ {sid}")
            else:
                print(f"✗ {sid}")
    print(f"Done. {len(working)}/{total} working.")
    return working

class ArabicRadioStations:
    def __init__(self):
        """
        Initialize the ArabicRadioStations object with empty station dictionaries.
        """
        self.stations_by_country = {}
        self.stations_by_city = {}
        self.city_country_map = {}

    def load_stations(self):
        """
        Load predefined stations for each country and city from arab_stations.json.
        """
        try:
            with open('arab_stations.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.stations_by_country = data.get('stations_by_country', {})
                self.stations_by_city = data.get('stations_by_city', {})
        except Exception as e:
            logger.error(f"Error loading stations: {e}")
            raise

    def get_all_stations(self):
        """
        Get all stations from both country and city sources as a single dictionary.
        """
        all_stations = {}
        for st in self.stations_by_country.values():
            all_stations.update(st)
        for st in self.stations_by_city.values():
            all_stations.update(st)
        return all_stations

    def get_stations_by_country(self, country_code):
        """
        Get stations for a specific country code.
        """
        return self.stations_by_country.get(country_code.upper(), {})

    def get_stations_by_city(self, city, skip_direct=False):
        """
        Get stations for a specific city name.
        """
        return self.stations_by_city.get(city.lower(), {})

    def search_stations_by_name(self, fragment):
        """
        Search for stations by a name fragment (case-insensitive).
        Returns a dictionary of matching station IDs and URLs.
        """
        frag = fragment.lower()
        res = {}
        for d in (self.stations_by_country, self.stations_by_city):
            for sts in d.values():
                for sid, url in sts.items():
                    if frag in sid.lower():
                        res[sid] = url
        return res

def main():
    """
    Main entry point for the script. Parses arguments, loads stations, and executes the requested action.
    """
    parser = argparse.ArgumentParser(description='Record Arabic radio stations')
    parser.add_argument('--duration', type=int, default=30)
    parser.add_argument('--country', type=str, help='Country code')
    parser.add_argument('--city', type=str, help='City name')
    parser.add_argument('--all-cities', action='store_true')
    parser.add_argument('--search', type=str)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--list-cities', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--timeout', type=int, default=5)
    parser.add_argument('--output', type=str, default='recordings')
    parser.add_argument('--workers', type=int, default=5)
    parser.add_argument('--skip-direct-urls', action='store_true')
    parser.add_argument('--export', type=str, help='Export stations to JSON')
    parser.add_argument('--import', dest='import_file', type=str)
    args = parser.parse_args()

    radio = ArabicRadioStations()
    
    # Load stations from JSON file
    try:
        radio.load_stations()
        print(f"Loaded stations from arab_stations.json")
    except Exception as e:
        print(f"Error loading stations: {e}")
        return

    # Import stations
    if args.import_file:
        try:
            with open(args.import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                radio.stations_by_country.update(data.get('stations_by_country', {}))
                radio.stations_by_city.update(data.get('stations_by_city', {}))
            print(f"Imported from {args.import_file}")
        except Exception as e:
            print(f"Error importing: {e}")

    if args.list_cities:
        print("Available cities:")
        for c, code in radio.city_country_map.items(): print(f" - {c} ({code.upper()})")
        return

    if args.all_cities:
        print(f"Fetching from all {len(radio.city_country_map)} cities...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as exe:
            futs = {exe.submit(fetch_worldradiomap_stations, code, city, not args.skip_direct_urls): city
                    for city, code in radio.city_country_map.items()}
            for fut in concurrent.futures.as_completed(futs):
                city = futs[fut]
                stations = fut.result()
                radio.stations_by_city[city] = stations

    if args.list:
        if args.country:
            sts = radio.get_stations_by_country(args.country)
        elif args.city:
            sts = radio.get_stations_by_city(args.city, skip_direct=args.skip_direct_urls)
        else:
            sts = radio.get_all_stations()
        print("Stations:")
        for sid in sts: print(f" - {sid}")
        return

    if args.search:
        res = radio.search_stations_by_name(args.search)
        print("Search results:")
        for sid, url in res.items(): print(f" - {sid}: {url}")
        return

    # Determine stations to record
    if args.country:
        stations = radio.get_stations_by_country(args.country)
    elif args.city:
        stations = radio.get_stations_by_city(args.city, skip_direct=args.skip_direct_urls)
    else:
        stations = radio.get_all_stations()

    if not stations:
        print("No stations found.")
        return

    # Verify if requested
    if args.verify:
        stations = verify_stations_health(stations, max_workers=args.workers)
        if not stations:
            print("No working stations found.")
            return

    # Export if requested
    if args.export:
        try:
            with open(args.export, 'w', encoding='utf-8') as f:
                json.dump({'stations_by_country': radio.stations_by_country,
                           'stations_by_city': radio.stations_by_city}, f, indent=2, ensure_ascii=False)
            print(f"Exported stations to {args.export}")
        except Exception as e:
            print(f"Error exporting: {e}")

    # Record each station
    for sid, url in stations.items():
        try:
            # Create city-specific folder if recording by city
            if args.city:
                city_folder = os.path.join(args.output, args.city.lower())
            else:
                city_folder = args.output
            
            record_stream(url, seconds=args.duration, folder=city_folder)
        except Exception:
            print(f"Failed to record {sid}")

if __name__ == "__main__":
    main()
