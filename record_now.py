#!/usr/bin/env python3
import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path
import csv
import time
import schedule

from arabic_radio_recorder import ArabicRadioStations, record_stream, verify_stations_health

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("recording.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("record_now")

def log_recording(log_file: str, sound_filename: str, duration: int, time_recorded: str, city: str):
    """Append a row to the CSV log file for each recording."""
    file_exists = os.path.isfile(log_file)
    with open(log_file, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["Sound filename", "Duration (seconds)", "Time recorded", "City"])
        writer.writerow([sound_filename, duration, time_recorded, city])

class CityRecorder:
    def __init__(self, stations_file: str = 'arab_stations.json', 
                 output_dir: str = 'recordings',
                 log_file: str = 'recordings_log.csv',
                 duration: int = 30):
        self.stations_file = stations_file
        self.output_dir = output_dir
        self.log_file = log_file
        self.duration = duration
        self.radio = ArabicRadioStations()
        self.working_stations = {}
        self.load_stations()
        
    def load_stations(self):
        """Load and verify all stations."""
        try:
            with open(self.stations_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.radio.stations_by_country.update(data.get('stations_by_country', {}))
                self.radio.stations_by_city.update(data.get('stations_by_city', {}))
            logger.info(f"Loaded stations from {self.stations_file}")
            
            # Get and verify all stations
            all_stations = self.radio.get_all_stations()
            logger.info(f"Found {len(all_stations)} total stations")
            
            self.working_stations = verify_stations_health(all_stations)
            logger.info(f"Found {len(self.working_stations)} working stations")
            
        except Exception as e:
            logger.error(f"Error loading stations: {e}")
            sys.exit(1)

    def record_city(self, city: str):
        """Record all stations for a specific city."""
        logger.info(f"Starting recording for city: {city}")
        city_dir = os.path.join(self.output_dir, city)
        os.makedirs(city_dir, exist_ok=True)
        
        successful = 0
        failed = 0
        
        # Filter stations for this city
        city_stations = {sid: url for sid, url in self.working_stations.items() 
                        if sid.split('-')[0].lower() == city.lower()}
        
        if not city_stations:
            logger.warning(f"No working stations found for {city}")
            return
        
        for sid, url in city_stations.items():
            try:
                # Record the station
                logger.info(f"Recording {sid}...")
                out_file = record_stream(url, seconds=self.duration, folder=city_dir)
                
                # Log the recording
                log_recording(
                    log_file=self.log_file,
                    sound_filename=str(out_file),
                    duration=self.duration,
                    time_recorded=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    city=city
                )
                
                successful += 1
                logger.info(f"Successfully recorded {sid}")
                
            except Exception as e:
                failed += 1
                logger.error(f"Failed to record {sid}: {e}")
        
        logger.info(f"Completed recording for {city}: {successful} successful, {failed} failed")

    def schedule_recordings(self):
        """Schedule recordings for all cities every 2 hours."""
        cities = self.get_cities()
        if not cities:
            logger.error("No cities found")
            return
        
        # Schedule recordings every 2 hours
        for hour in range(0, 24, 2):
            time_str = f"{hour:02d}:00"
            for city in cities:
                schedule.every().day.at(time_str).do(self.record_city, city)
            logger.info(f"Scheduled recordings for all cities at {time_str}")
        
        logger.info(f"Scheduled {len(cities)} cities for recording every 2 hours")
        logger.info("Recording times: " + ", ".join(f"{h:02d}:00" for h in range(0, 24, 2)))

    def get_cities(self) -> list:
        """Get list of available cities."""
        cities = set()
        for sid in self.working_stations.keys():
            city = sid.split('-')[0]
            cities.add(city)
        return sorted(list(cities))

    def list_cities_and_stations(self):
        """List all cities and their working stations."""
        cities = self.get_cities()
        if not cities:
            logger.error("No cities found")
            return
        
        print("\nTarget Cities and Their Stations:")
        print("=" * 50)
        for city in sorted(cities):
            city_stations = {sid: url for sid, url in self.working_stations.items() 
                           if sid.split('-')[0].lower() == city.lower()}
            print(f"\n{city} ({len(city_stations)} stations):")
            for sid in sorted(city_stations.keys()):
                print(f"  - {sid}")
        print("\n" + "=" * 50)
        print(f"Total Cities: {len(cities)}")
        print(f"Total Working Stations: {len(self.working_stations)}")

    def run(self):
        """Run the scheduler."""
        logger.info("Starting scheduled recorder")
        while True:
            schedule.run_pending()
            time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description='Record radio stations every 2 hours')
    parser.add_argument('--stations', type=str, default='arab_stations.json',
                      help='JSON file containing station data')
    parser.add_argument('--output', type=str, default='recordings',
                      help='Output directory for recordings')
    parser.add_argument('--log', type=str, default='recordings_log.csv',
                      help='CSV file to log recordings')
    parser.add_argument('--duration', type=int, default=30,
                      help='Duration of each recording in seconds')
    parser.add_argument('--list-times', action='store_true',
                      help='List scheduled recording times and exit')
    parser.add_argument('--list-cities', action='store_true',
                      help='List cities and their stations')
    
    args = parser.parse_args()
    
    recorder = CityRecorder(
        stations_file=args.stations,
        output_dir=args.output,
        log_file=args.log,
        duration=args.duration
    )
    
    if args.list_cities:
        recorder.list_cities_and_stations()
        return
    
    if args.list_times:
        recorder.schedule_recordings()
        return
    
    recorder.list_cities_and_stations()  # Show cities before starting
    recorder.schedule_recordings()
    recorder.run()

if __name__ == "__main__":
    main() 