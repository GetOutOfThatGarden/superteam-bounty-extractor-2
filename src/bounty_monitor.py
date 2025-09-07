import asyncio
import time
from bounty_api_client import get_new_bounties_only, save_bounty_data
from bounty_scraper import ImprovedSuperteamBountyScraper

async def monitor_and_scrape():
    """Check for new bounties and scrape them"""
    print("🔍 Checking for new bounties...")
    
    # Get new bounties from API
    new_bounties = get_new_bounties_only()
    
    if not new_bounties:
        print("No new bounties found.")
        return
    
    # Save new bounty data
    save_bounty_data(new_bounties)
    
    # Scrape new bounties only
    scraper = ImprovedSuperteamBountyScraper()
    await scraper.scrape_new_bounties_only()
    
    print(f"✅ Successfully processed {len(new_bounties)} new bounties")

if __name__ == "__main__":
    asyncio.run(monitor_and_scrape())