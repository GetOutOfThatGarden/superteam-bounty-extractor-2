#!/usr/bin/env python3
"""
Superteam Bounty Extractor - Main Entry Point

This script runs the complete bounty monitoring workflow:
1. Fetch new bounties from API
2. Scrape bounty details
3. Extract prize information
4. Merge prize data into bounty descriptions
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from bounty_api_client import get_new_bounties_only, save_bounty_data
from bounty_scraper import ImprovedSuperteamBountyScraper
from prize_extractor import PrizeExtractor
import json
import time

async def main():
    """
    Main workflow function that runs all bounty processing steps
    """
    print("🚀 Starting Superteam Bounty Extractor Workflow")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Step 1: Fetch new bounties from API
        print("\n📡 Step 1: Fetching new bounties from API...")
        new_bounties = get_new_bounties_only()
        
        if not new_bounties:
            print("✅ No new bounties found. Workflow complete.")
            return
        
        print(f"✅ Found {len(new_bounties)} new bounties")
        
        # Step 2: Save bounty data
        print("\n💾 Step 2: Saving bounty data...")
        save_bounty_data(new_bounties)
        print("✅ Bounty data saved successfully")
        
        # Step 3: Scrape bounty details
        print("\n🕷️  Step 3: Scraping bounty details...")
        scraper = ImprovedSuperteamBountyScraper()
        await scraper.scrape_new_bounties_only()
        print("✅ Bounty scraping completed")
        
        # Step 4: Extract prize information
        print("\n🎯 Step 4: Extracting prize information...")
        prize_extractor = PrizeExtractor()
        
        # Get URLs from new bounties
        bounty_urls = []
        for bounty in new_bounties:
            if 'url' in bounty:
                bounty_urls.append(bounty['url'])
            elif 'slug' in bounty:
                # Construct URL from slug
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
            
            print(f"✅ Prize extraction completed:")
            print(f"   • Total bounties processed: {len(prize_results)}")
            print(f"   • Successful extractions: {len([r for r in prize_results if r.get('amounts_match')])}")
            print(f"   • Results saved to: {prize_filename}")
            
            # Step 5: Merge prize data into bounty descriptions
            print("\n🔄 Step 5: Merging prize data into bounty descriptions...")
            success = prize_extractor.update_bounty_descriptions_with_prizes()
            
            if success:
                print("✅ Prize data successfully merged into bounty descriptions")
            else:
                print("⚠️  Warning: Prize data merge encountered issues")
            
            # Print summary of each bounty
            print("\n📊 Bounty Processing Summary:")
            for result in prize_results:
                status = "✅" if result.get('amounts_match') else "⚠️"
                title = result['title'][:50] + "..." if len(result['title']) > 50 else result['title']
                print(f"   {status} {title}")
                print(f"      Total: {result['total_reward']}, Individual Sum: {result['individual_sum']}")
        
        else:
            print("⚠️  No valid URLs found for prize extraction")
        
        print("\n" + "=" * 60)
        print(f"🎉 Workflow completed successfully! Processed {len(new_bounties)} new bounties")
        print(f"📅 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ Error in workflow: {e}")
        print("Please check the logs and try again.")
        sys.exit(1)

def run_workflow():
    """
    Convenience function to run the async workflow
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Workflow interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()