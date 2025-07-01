#!/usr/bin/env python3
import argparse
import asyncio
import datetime
import json
import logging
import os
import random
import sys
import time
from typing import List, Dict, Set
import schedule
import csv
from pathlib import Path

from arabic_radio_recorder import ArabicRadioStations, record_stream, verify_stations_health

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduled_recorder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("scheduled_recorder")

class StationMonitor:
    def __init__(self, max_retries: int = 3, retry_delay: int = 300):
        self.max_retries = max_retries
        self.retry_delay = retry_delay  # seconds
        self.failed_stations: Dict[str, int] = {}  # station_id -> retry count
        self.working_stations: Set[str] = set()
        self.last_verification: Dict[str, datetime.datetime] = {}

    def mark_failed(self, station_id: str):
        """Mark a station as failed and track retry attempts."""
        if station_id in self.working_stations:
            self.working_stations.remove(station_id)
        self.failed_stations[station_id] = self.failed_stations.get(station_id, 0) + 1

    def mark_working(self, station_id: str):
        """Mark a station as working."""
        self.working_stations.add(station_id)
        if station_id in self.failed_stations:
            del self.failed_stations[station_id]
        self.last_verification[station_id] = datetime.datetime.now()

    def should_retry(self, station_id: str) -> bool:
        """Check if a failed station should be retried."""
        return self.failed_stations.get(station_id, 0) < self.max_retries

    def get_retry_delay(self, station_id: str) -> int:
        """Get the delay before next retry attempt."""
        return self.retry_delay * (self.failed_stations.get(station_id, 0) + 1)

    def get_status_report(self) -> str:
        """Generate a status report of all stations."""
        total = len(self.working_stations) + len(self.failed_stations)
        working = len(self.working_stations)
        failed = len(self.failed_stations)
        return f"Status Report:\nWorking: {working}/{total}\nFailed: {failed}/{total}"

class ScheduledRecorder:
    def __init__(self, stations_file: str, base_output_dir: str = "recordings", log_file: str = "recordings_log.csv"):
        self.radio = ArabicRadioStations()
        self.base_output_dir = base_output_dir
        self.log_file = log_file
        self.monitor = StationMonitor()
        self.load_stations(stations_file)
        self.recording_times: Dict[str, List[str]] = {}
        
    def load_stations(self, stations_file: str):
        """Load stations from JSON file and verify initial state."""
        try:
            with open(stations_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.radio.stations_by_country.update(data.get('stations_by_country', {}))
                self.radio.stations_by_city.update(data.get('stations_by_city', {}))
            logger.info(f"Loaded stations from {stations_file}")
            
            # Verify initial state of stations
            self.verify_all_stations()
        except Exception as e:
            logger.error(f"Error loading stations: {e}")
            sys.exit(1)

    def verify_all_stations(self):
        """Verify all stations and update monitor."""
        logger.info("Verifying all stations...")
        all_stations = self.radio.get_all_stations()
        working_stations = verify_stations_health(all_stations)
        
        for sid in all_stations:
            if sid in working_stations:
                self.monitor.mark_working(sid)
            else:
                self.monitor.mark_failed(sid)
        
        logger.info(self.monitor.get_status_report())

    def get_cities(self) -> List[str]:
        """Get list of available cities."""
        cities = list(self.radio.stations_by_city.keys())
        if not cities:
            logger.error("No cities found in the station data")
            # Try to load cities from the JSON file directly
            try:
                with open('arab_stations.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cities = list(data.get('stations_by_city', {}).keys())
            except Exception as e:
                logger.error(f"Failed to load cities from JSON: {e}")
        return cities

    def schedule_city_recording(self, city: str, time_str: str):
        """Schedule recording for a specific city at a specific time."""
        schedule.every().day.at(time_str).do(self.record_city, city)
        logger.info(f"Scheduled recording for {city} at {time_str}")

    def log_recording(self, sound_filename: str, duration: int, time_recorded: str, city: str):
        """Append a row to the CSV log file for each recording."""
        file_exists = os.path.isfile(self.log_file)
        with open(self.log_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["Sound filename", "Duration (seconds)", "Time recorded", "City"])
            writer.writerow([sound_filename, duration, time_recorded, city])

    def record_city(self, city: str):
        """Record all stations for a specific city."""
        logger.info(f"Starting recording for city: {city}")
        output_dir = os.path.join(self.base_output_dir, city)
        os.makedirs(output_dir, exist_ok=True)

        # Get stations for the city
        stations = self.radio.get_stations_by_city(city)
        if not stations:
            logger.warning(f"No stations found for {city}")
            return

        # Verify stations
        working_stations = verify_stations_health(stations)
        if not working_stations:
            logger.warning(f"No working stations found for {city}")
            return

        # Record each station
        for sid, url in working_stations.items():
            try:
                duration = 30
                out_file = record_stream(url, seconds=duration, folder=output_dir)
                logger.info(f"Successfully recorded {sid}")
                self.monitor.mark_working(sid)
                self.log_recording(
                    sound_filename=str(out_file),
                    duration=duration,
                    time_recorded=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    city=city
                )
            except Exception as e:
                logger.error(f"Failed to record {sid}: {e}")
                self.monitor.mark_failed(sid)
                if self.monitor.should_retry(sid):
                    retry_delay = self.monitor.get_retry_delay(sid)
                    logger.info(f"Scheduling retry for {sid} in {retry_delay} seconds")
                    schedule.every(retry_delay).seconds.do(self.retry_recording, sid, url, city)

    def retry_recording(self, sid: str, url: str, city: str):
        """Retry recording a failed station."""
        try:
            duration = 30
            output_dir = os.path.join(self.base_output_dir, city)
            out_file = record_stream(url, seconds=duration, folder=output_dir)
            logger.info(f"Successfully recorded {sid} on retry")
            self.monitor.mark_working(sid)
            self.log_recording(
                sound_filename=str(out_file),
                duration=duration,
                time_recorded=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                city=city
            )
        except Exception as e:
            logger.error(f"Failed to record {sid} on retry: {e}")
            self.monitor.mark_failed(sid)

    def schedule_all_cities(self, start_hour: int = 0, end_hour: int = 24, interval_minutes: int = 30):
        """Schedule recordings for all cities at random times within the given interval."""
        cities = self.get_cities()
        if not cities:
            logger.error("No cities available")
            return

        # Calculate number of slots available
        total_minutes = (end_hour - start_hour) * 60
        slots = total_minutes // interval_minutes
        
        if slots < len(cities):
            logger.warning(f"Not enough time slots ({slots}) for all cities ({len(cities)})")
            # Reduce interval to fit all cities
            interval_minutes = total_minutes // len(cities)
            slots = len(cities)

        # Generate random times for each city
        times = []
        for i in range(slots):
            minutes = start_hour * 60 + i * interval_minutes
            hour = minutes // 60
            minute = minutes % 60
            times.append(f"{hour:02d}:{minute:02d}")

        # Shuffle times and assign to cities
        random.shuffle(times)
        for city, time_str in zip(cities, times):
            self.schedule_city_recording(city, time_str)
            self.recording_times[city] = time_str

    def run(self):
        """Run the scheduler with periodic status checks."""
        logger.info("Starting scheduled recorder")
        
        # Schedule periodic status report
        schedule.every(1).hours.do(self.print_status_report)
        
        while True:
            schedule.run_pending()
            time.sleep(1)

    def print_status_report(self):
        """Print current status report."""
        logger.info(self.monitor.get_status_report())

def main():
    parser = argparse.ArgumentParser(description='Schedule radio station recordings for different cities')
    parser.add_argument('--stations', type=str, default='arab_stations.json',
                      help='JSON file containing station data')
    parser.add_argument('--output', type=str, default='recordings',
                      help='Base output directory for recordings')
    parser.add_argument('--log', type=str, default='recordings_log.csv',
                      help='CSV file to log recordings')
    parser.add_argument('--start-hour', type=int, default=0,
                      help='Start hour for scheduling (0-23)')
    parser.add_argument('--end-hour', type=int, default=24,
                      help='End hour for scheduling (0-24)')
    parser.add_argument('--interval', type=int, default=30,
                      help='Interval between recordings in minutes')
    parser.add_argument('--list-times', action='store_true',
                      help='List scheduled recording times and exit')
    parser.add_argument('--verify-only', action='store_true',
                      help='Only verify stations and exit')

    # --- addition ---
    parser.add_argument('--repeat-every', type=int, help='Repeat recording every X minutes for all cities')

    args = parser.parse_args()

    recorder = ScheduledRecorder(args.stations, args.output, args.log)
    
    if args.verify_only:
        recorder.verify_all_stations()
        return

    if args.list_times:
        recorder.schedule_all_cities(args.start_hour, args.end_hour, args.interval)
        print("\nScheduled recording times:")
        for city, time in recorder.recording_times.items():
            print(f"{city}: {time}")
        return

    if args.repeat_every:
        cities = recorder.get_cities()
        for city in cities:
            schedule.every(args.repeat_every).minutes.do(recorder.record_city, city)
        recorder.run()
        return

    recorder.schedule_all_cities(args.start_hour, args.end_hour, args.interval)
    recorder.run()

if __name__ == "__main__":
    main() 