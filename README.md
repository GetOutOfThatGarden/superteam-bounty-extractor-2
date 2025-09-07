# Superteam Bounty Extractor

A comprehensive Python tool to automatically extract, monitor, and analyze bounties from [earn.superteam.fun](https://earn.superteam.fun) with detailed scraping capabilities and prize extraction.

## Features

- 🔍 **API Integration**: Fetches bounty data directly from Superteam's API
- 🕷️ **Web Scraping**: Extracts detailed bounty descriptions and metadata using Playwright
- 💰 **Prize Extraction**: Automatically extracts individual prize breakdowns and total rewards
- 📊 **Smart Monitoring**: Only processes new bounties to avoid duplicates
- 💾 **Data Persistence**: Saves bounty data in JSON format and tracks processed bounties
- 🔗 **Link Extraction**: Generates direct links to bounty pages for easy access
- ⚡ **Async Processing**: Efficient asynchronous scraping for better performance
- 🎯 **Complete Workflow**: Orchestrated pipeline from API fetching to prize extraction

## Project Structure

superteam-bounty-extractor/
├── main.py                     # Main orchestrator script - runs complete workflow
├── src/
│   ├── bounty_api_client.py    # API client for fetching bounty data
│   ├── bounty_monitor.py       # Monitoring and orchestration script
│   ├── bounty_scraper.py       # Web scraper for detailed bounty extraction
│   └── prize_extractor.py      # Prize breakdown and reward extraction
├── data/
│   ├── bounty_links.txt        # Generated bounty URLs
│   ├── processed_bounties.json # Tracking processed bounties
│   └── superteam_bounties.json # Raw bounty data from API
├── output/
│   └── bounty_descriptions.json # Complete bounty data with prizes
├── prize_extraction_results_*.json # Prize extraction results with timestamps
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

### Complete Workflow (Recommended)

Run the main orchestrator to execute the complete bounty extraction pipeline:

```bash
python main.py
```

This will:
1. Fetch bounties from the API
2. Scrape detailed descriptions
3. Extract prize breakdowns
4. Merge all data into `output/bounty_descriptions.json`

### Individual Components

**Run bounty monitoring only**:
```bash
cd src
python bounty_monitor.py
```

**Extract prizes from existing bounties**:
```bash
cd src
python prize_extractor.py
```

**Run as a module**:
```bash
# First create __init__.py in src directory
touch src/__init__.py

# Then run as module
python -m src.bounty_monitor
```

## How It Works

1. **API Fetching**: Connects to Superteam's API to fetch the latest bounty data
2. **New Bounty Detection**: Compares with previously processed bounties to identify new ones
3. **Link Generation**: Creates direct URLs to bounty pages on earn.superteam.fun
4. **Web Scraping**: Uses Playwright to extract detailed bounty descriptions and metadata
5. **Prize Extraction**: Analyzes bounty pages to extract individual prize amounts and breakdowns
6. **Data Merging**: Combines all extracted data into comprehensive bounty profiles
7. **Data Storage**: Saves all data in structured JSON format for further processing

## Prize Extraction Features

The prize extractor includes:
- **Multiple Extraction Strategies**: Uses various HTML parsing methods for robust extraction
- **Range Position Handling**: Expands ranges like "5th - 10th" into individual positions
- **Token Type Detection**: Identifies prize currencies (USDC, SOL, etc.)
- **Validation**: Verifies extracted amounts match expected totals
- **Error Handling**: Graceful handling of missing or malformed prize data

## Output Files

- **`output/bounty_descriptions.json`**: Complete bounty data including descriptions and extracted prizes
- **`prize_extraction_results_*.json`**: Detailed prize extraction results with timestamps
- **`data/superteam_bounties.json`**: Raw bounty data from the API
- **`data/bounty_links.txt`**: Direct links to all bounty pages
- **`data/processed_bounties.json`**: IDs of bounties that have been processed

## Configuration

The tool automatically handles:
- Missing data directories (creates them as needed)
- First-time runs (initializes tracking files)
- Error handling for network issues and missing files
- URL domain corrections for proper prize extraction

## Dependencies

- **requests**: For API communication
- **playwright**: For web scraping with browser automation
- **asyncio**: For asynchronous processing
- **json**: For data serialization
- **re**: For regex pattern matching in prize extraction

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Make sure you're running from the correct directory or have created `__init__.py` in the src folder

2. **FileNotFoundError for data files**: The tool will automatically create missing data files on first run

3. **Playwright browser issues**: Run `playwright install` to ensure browsers are properly installed

4. **Prize extraction failures**: Check that bounty URLs use the correct domain (earn.superteam.fun)

5. **Empty prize data**: Ensure bounties have loaded completely before extraction

### Running from Different Directories

For individual components, the recommended approach is to run from the `src` directory:

```bash
cd src
python bounty_monitor.py
```

For the complete workflow, run from the project root:

```bash
python main.py
```

## Example Output

The tool generates comprehensive bounty data including:

```json
{
  "title": "Build a Solana DeFi Dashboard",
  "slug": "build-solana-defi-dashboard",
  "url": "https://earn.superteam.fun/listings/bounty/build-solana-defi-dashboard",
  "description": "Create a comprehensive dashboard...",
  "reward_amount": "$5,000 USDC",
  "extracted_prize_data": {
    "total_reward": "5000",
    "prize_breakdown": [
      {"position": "1st", "amount": "3000"},
      {"position": "2nd", "amount": "1500"},
      {"position": "3rd", "amount": "500"}
    ],
    "token_type": "USDC",
    "individual_sum": "5000",
    "amounts_match": true
  }
}
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

See LICENSE file for details.