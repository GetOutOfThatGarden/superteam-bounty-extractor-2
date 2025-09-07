import asyncio
import time
from bounty_api_client import get_new_bounties_only, save_bounty_data
from bounty_scraper import ImprovedSuperteamBountyScraper
from prize_extractor import PrizeExtractor
import json

async def monitor_and_scrape():
    """Check for new bounties, scrape them, and extract prize information"""
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
    
    # Extract prize information for new bounties
    print("\n🎯 Starting prize extraction for new bounties...")
    prize_extractor = PrizeExtractor()
    
    # Get URLs from new bounties
    bounty_urls = []
    for bounty in new_bounties:
        if 'url' in bounty:
            bounty_urls.append(bounty['url'])
        elif 'slug' in bounty:
            # Construct URL from slug if needed - FIXED: Use correct domain
            bounty_urls.append(f"https://earn.superteam.fun/listing/{bounty['slug']}")
    
    if bounty_urls:
        # Extract prize information
        prize_results = await prize_extractor.process_bounties_with_prizes(bounty_urls)
        
        # Save prize extraction results
        prize_filename = f"prize_extraction_results_{int(time.time())}.json"
        with open(prize_filename, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'total_bounties': len(prize_results),
                'successful_extractions': len([r for r in prize_results if r.get('amounts_match')]),
                'results': prize_results
            }, f, indent=2)
        
        print(f"\n📊 Prize extraction completed:")
        print(f"  • Total bounties processed: {len(prize_results)}")
        print(f"  • Successful extractions: {len([r for r in prize_results if r.get('amounts_match')])}")
        print(f"  • Results saved to: {prize_filename}")
        
        # Print summary of each bounty
        for result in prize_results:
            status = "✅" if result.get('amounts_match') else "⚠️"
            print(f"  {status} {result['title']}: Total={result['total_reward']}, Individual Sum={result['individual_sum']}")
    
    print(f"\n✅ Successfully processed {len(new_bounties)} new bounties with prize extraction")

if __name__ == "__main__":
    asyncio.run(monitor_and_scrape())