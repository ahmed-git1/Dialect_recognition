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
from radios import RadioBrowser

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

def find_stream(name: str, country: str | None = None) -> str:
    """Find a radio stream URL using the RadioBrowser API."""
    async def _search() -> str:
        async with RadioBrowser(user_agent="Recorder/1.0") as rb:
            stations = await rb.search(name=name, limit=50)
            if country:
                stations = [s for s in stations if s.countrycode and s.countrycode.lower() == country.lower()]
            if not stations:
                raise RuntimeError(f"No stream found for {name} in {country if country else 'any country'}")
            return stations[0].url_resolved
    return asyncio.run(_search())

def record_stream(url: str, seconds: int = 30, folder: str = "recordings") -> pathlib.Path:
    """Record a stream for the specified number of seconds using FFmpeg."""
    os.makedirs(folder, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_file = pathlib.Path(folder) / f"radio_{ts}.mp3"

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
        "-i", url,
        "-t", str(seconds),
        "-c", "copy",
        out_file.as_posix()
    ]
    
    print(f"Recording {url} for {seconds} seconds...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Successfully saved to {out_file}")
        return out_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Error recording stream {url}: {e}")
        print(f"FFmpeg error: {e.stderr}")
        raise

def verify_stream_url(url, timeout=5):
    """
    Verify if a stream URL is working.
    Returns True if working, False otherwise.
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
        audio = soup.find('audio')
        if audio:
            src = audio.find('source')
            if src and src.has_attr('src'):
                return src['src']
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith(('.mp3', '.m3u8', '.aac', '.pls')) or 'stream' in href or 'listen' in href:
                return href if href.startswith('http') else f"https://worldradiomap.com{href}"
        for script in soup.find_all('script'):
            if script.string:
                match = re.search(r"(https?://[^\s'\"]+\.(mp3|m3u8|aac|pls))", script.string)
                if match:
                    return match.group(1)
        return None
    except Exception as e:
        logger.error(f"Error extracting direct stream URL from {play_page_url}: {e}")
        return None

def fetch_worldradiomap_stations(country_code, city, get_direct_urls=True):
    """
    Fetch radio stations from WorldRadioMap for a specific city.
    Returns a dict of station_id -> url.
    """
    stations = {}
    url = f"https://worldradiomap.com/{country_code}/{city}"
    logger.info(f"Fetching radio stations from {url}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code} for {url}")
            return stations
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        for a in soup.select('td a'):
            name = a.get_text(strip=True)
            href = a.get('href')
            if name and href and 'play' in href:
                links.append((name, href if href.startswith('http') else f"https://worldradiomap.com{href}"))
        if get_direct_urls:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(extract_direct_stream_url, u): (n, u) for n, u in links}
                for future in concurrent.futures.as_completed(futures):
                    name, page = futures[future]
                    url_direct = future.result() or page
                    clean = re.sub(r'[^\w\s-]', '', name).lower().strip()
                    clean = re.sub(r'[\s]+', '-', clean)
                    sid = f"{clean}-{city}-{country_code}"
                    stations[sid] = url_direct
        else:
            for name, page in links:
                clean = re.sub(r'[^\w\s-]', '', name).lower().strip()
                clean = re.sub(r'[\s]+', '-', clean)
                sid = f"{clean}-{city}-{country_code}"
                stations[sid] = page
        return stations
    except Exception as e:
        logger.error(f"Error fetching stations for {city}: {e}")
        return stations

def verify_stations_health(stations_dict, max_workers=5):
    """Verify the health of all stations in parallel."""
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
    """A collection of Arabic radio stations from various countries."""
    def __init__(self):
        self.stations_by_country = {}
        self.stations_by_city = {}
        self.city_country_map = {
            # ... (mapping omitted for brevity, same as defined earlier) ...
        }
        self.load_stations()

    def load_stations(self):
        """Load predefined stations for each country."""
        # Predefined stations as in initial code
        # (same dictionaries for saudi_stations, uae_stations, etc.)
        self.stations_by_country = {
            # ... same as initial load_stations content ...
        }

    def get_all_stations(self):
        all_stations = {}
        for st in self.stations_by_country.values(): all_stations.update(st)
        for st in self.stations_by_city.values(): all_stations.update(st)
        return all_stations

    def get_stations_by_country(self, country_code):
        return self.stations_by_country.get(country_code.upper(), {})

    def get_stations_by_city(self, city, skip_direct=False):
        city = city.lower()
        if city not in self.stations_by_city and city in self.city_country_map:
            code = self.city_country_map[city]
            self.stations_by_city[city] = fetch_worldradiomap_stations(code, city, get_direct_urls=not skip_direct)
        return self.stations_by_city.get(city, {})

    def search_stations_by_name(self, fragment):
        frag = fragment.lower()
        res = {}
        for d in (self.stations_by_country, self.stations_by_city):
            for sts in d.values():
                for sid, url in sts.items():
                    if frag in sid.lower(): res[sid] = url
        return res

def main():
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
            record_stream(url, seconds=args.duration, folder=args.output)
        except Exception:
            print(f"Failed to record {sid}")

if __name__ == "__main__":
    main()
