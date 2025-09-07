# Superteam Bounty Extractor

A Python tool to automatically extract and monitor bounties from [earn.superteam.fun](https://earn.superteam.fun) with detailed scraping capabilities.

## Features

- 🔍 **API Integration**: Fetches bounty data directly from Superteam's API
- 🕷️ **Web Scraping**: Extracts detailed bounty descriptions and metadata using Playwright
- 📊 **Smart Monitoring**: Only processes new bounties to avoid duplicates
- 💾 **Data Persistence**: Saves bounty data in JSON format and tracks processed bounties
- 🔗 **Link Extraction**: Generates direct links to bounty pages for easy access
- ⚡ **Async Processing**: Efficient asynchronous scraping for better performance

## Project Structure

superteam-bounty-extractor/
├── src/
│   ├── bounty_api_client.py    # API client for fetching bounty data
│   ├── bounty_monitor.py       # Main monitoring and orchestration script
│   └── bounty_scraper.py       # Web scraper for detailed bounty extraction
├── data/
│   ├── bounty_links.txt        # Generated bounty URLs
│   ├── processed_bounties.json # Tracking processed bounties
│   └── superteam_bounties.json # Raw bounty data from API
├── output/                     # Scraped bounty details
└── requirements.txt


## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd superteam-bounty-extractor
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install
   ```

## Usage

### Basic Usage

Run the bounty monitor to check for new bounties and scrape them:

```bash
cd src
python bounty_monitor.py
```

### Running as a Module

Alternatively, you can run it as a Python module from the project root:

```bash
# First create __init__.py in src directory
touch src/__init__.py

# Then run as module
python -m src.bounty_monitor
```

## How It Works

1. **API Fetching**: The tool connects to Superteam's API to fetch the latest bounty data
2. **New Bounty Detection**: Compares with previously processed bounties to identify new ones
3. **Link Generation**: Creates direct URLs to bounty pages on earn.superteam.fun
4. **Web Scraping**: Uses Playwright to extract detailed bounty descriptions and metadata
5. **Data Storage**: Saves all data in structured JSON format for further processing

## Output Files

- **`data/superteam_bounties.json`**: Raw bounty data from the API
- **`data/bounty_links.txt`**: Direct links to all bounty pages
- **`data/processed_bounties.json`**: IDs of bounties that have been processed
- **`output/`**: Directory containing detailed scraped bounty information

## Configuration

The tool automatically handles:
- Missing data directories (creates them as needed)
- First-time runs (initializes tracking files)
- Error handling for network issues and missing files

## Dependencies

- **requests**: For API communication
- **playwright**: For web scraping with browser automation
- **asyncio**: For asynchronous processing

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Make sure you're running from the correct directory or have created `__init__.py` in the src folder

2. **FileNotFoundError for data files**: The tool will automatically create missing data files on first run

3. **Playwright browser issues**: Run `playwright install` to ensure browsers are properly installed

### Running from Different Directories

If you encounter path issues, the recommended approach is to run from the `src` directory:

```bash
cd src
python bounty_monitor.py
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

See LICENSE file for details.