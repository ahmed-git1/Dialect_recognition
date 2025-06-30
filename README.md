# Arabic Radio Stations Recorder

A comprehensive tool for discovering and recording radio stations from Arab cities. This system allows you to record radio streams from various Arabic-speaking countries and cities, with support for scheduling, verification, and visualization.

## 🌟 Features

- **Multi-City Recording**: Record from specific cities or countries
- **Station Verification**: Check if radio stations are working before recording
- **Scheduled Recording**: Automate recordings at specific times
- **Interactive Map**: Visualize radio station coverage across the Arab world
- **Playlist Support**: Handle .pls, .m3u, and .m3u8 playlist files
- **HTML Page Extraction**: Automatically extract streaming URLs from HTML pages
- **Parallel Processing**: Record multiple stations simultaneously
- **Logging**: Comprehensive logging for debugging and monitoring

## 📁 File Structure

### Core Files
- `arabic_radio_recorder.py` - Main radio recorder script
- `arab_stations.json` - Database of radio stations by country and city
- `requirements.txt` - Python dependencies

### Utility Scripts
- `list_cities_from_json.py` - Extract and list cities from the JSON database
- `map_arab_cities.py` - Create interactive map visualization
- `record_now.py` - Immediate recording script
- `scheduled_recorder.py` - Scheduled recording functionality
- `test_radio_station.py` - Station testing and verification

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/omarnj-lab/Dialect_recognition.git
cd Dialect_recognition
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install FFmpeg (Required for audio recording)

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [https://ffmpeg.org/](https://ffmpeg.org/)

### 4. Verify Installation
```bash
python arabic_radio_recorder.py --help
```

## 📖 Usage Examples

### Basic Commands

#### List Available Cities
```bash
python list_cities_from_json.py
```

#### Record from a Specific City (30 seconds)
```bash
python arabic_radio_recorder.py --city jeddah --duration 30
```

#### Record from a Specific Country
```bash
python arabic_radio_recorder.py --country SA --duration 30
```

#### List All Stations
```bash
python arabic_radio_recorder.py --list
```

#### Search for Specific Stations
```bash
python arabic_radio_recorder.py --search "quran"
```

#### Verify Station Health Before Recording
```bash
python arabic_radio_recorder.py --city jeddah --verify --duration 30
```

### Advanced Features

#### Create Interactive Map
```bash
python map_arab_cities.py
```
This creates `arab_cities_map.html` with an interactive map showing all cities.

#### Scheduled Recording
```bash
python scheduled_recorder.py
```

#### Immediate Recording
```bash
python record_now.py
```

## 🎯 What's New in This Version

### ✅ Fixed Issues
- **HTML Page Handling**: Now properly extracts streaming URLs from HTML pages (`.htm` files)
- **PLS File Parsing**: Correctly parses playlist files before passing to FFmpeg
- **City-Specific Folders**: Recordings are now saved in city-specific subfolders (e.g., `recordings/jeddah/`)
- **URL Construction**: Fixed malformed URLs with proper path resolution

### 🔧 Technical Improvements
- Enhanced streaming URL extraction from WorldRadioMap pages
- Better error handling for network issues
- Improved playlist file parsing
- More robust HTML page scraping

## 📊 Supported Cities and Countries

### Countries
- **SA** - Saudi Arabia
- **EG** - Egypt  
- **AE** - United Arab Emirates
- **QA** - Qatar
- **KW** - Kuwait
- **JO** - Jordan
- **LB** - Lebanon
- **TN** - Tunisia
- **MA** - Morocco
- **DZ** - Algeria
- **LY** - Libya
- **SD** - Sudan
- **YE** - Yemen
- **IQ** - Iraq
- **SY** - Syria
- **PS** - Palestine
- **BH** - Bahrain
- **OM** - Oman
- **IR** - Iran
- **TR** - Turkey

### Major Cities
- **Jeddah, Riyadh, Mecca, Medina** (Saudi Arabia)
- **Cairo, Alexandria, Aswan, Luxor** (Egypt)
- **Dubai, Abu Dhabi, Sharjah** (UAE)
- **Doha** (Qatar)
- **Kuwait City** (Kuwait)
- **Amman** (Jordan)
- **Beirut** (Lebanon)
- **Tunis** (Tunisia)
- **Casablanca, Rabat, Marrakech** (Morocco)
- **Algiers** (Algeria)
- **And many more...**

## 🛠️ Command Line Options

### `arabic_radio_recorder.py`
- `--duration` - Recording duration in seconds (default: 30)
- `--country` - Country code (e.g., SA, EG, AE)
- `--city` - City name (e.g., jeddah, cairo, dubai)
- `--all-cities` - Record from all available cities
- `--search` - Search stations by name fragment
- `--list` - List available stations
- `--list-cities` - List available cities
- `--verify` - Verify station health before recording
- `--timeout` - Timeout for verification (default: 5)
- `--output` - Output directory (default: recordings)
- `--workers` - Number of parallel workers (default: 5)
- `--skip-direct-urls` - Skip direct URL stations
- `--export` - Export stations to JSON file
- `--import` - Import stations from JSON file

## 📁 Output Structure

### Recordings
```
recordings/
├── jeddah/
│   ├── radio_20250630_161116.mp3
│   ├── radio_20250630_161140.mp3
│   └── ...
├── cairo/
│   ├── radio_20250630_162000.mp3
│   └── ...
└── ...
```

### Logs
- `radio_recorder.log` - Main application log
- `scheduled_recorder.log` - Scheduled recording log

## 🔧 Troubleshooting

### Common Issues

#### 1. FFmpeg Not Found
```bash
# Verify FFmpeg installation
ffmpeg -version
```

#### 2. Network Issues
- Some radio streams may be temporarily unavailable
- This is normal for radio streaming - URLs change frequently
- The system handles failures gracefully

#### 3. Encoding Issues
- Ensure your terminal supports UTF-8
- Arabic city names are handled automatically

#### 4. Permission Issues
```bash
# Make scripts executable (Linux/macOS)
chmod +x *.py
```

### Success Rate Expectations
- **Typical success rate**: 20-40% of stations
- **This is normal** for radio streaming due to:
  - Frequent URL changes
  - Temporary server issues
  - Network connectivity problems
  - Some stations going offline

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source. Please check the license file for details.

## 🙏 Acknowledgments

- WorldRadioMap for providing radio station data
- FFmpeg for audio processing capabilities
- The Arabic radio community for maintaining these streams

## 📞 Support

For issues and questions:
1. Check the logs in `radio_recorder.log`
2. Verify your internet connection
3. Ensure all dependencies are installed
4. Check that FFmpeg is working: `ffmpeg -version`

## 🌐 Repository

Visit the repository at: [https://github.com/omarnj-lab/Dialect_recognition](https://github.com/omarnj-lab/Dialect_recognition)

---

**Note**: This tool is designed for research and educational purposes. Please respect the terms of service of the radio stations you record from. 