import json
import asyncio
import time
from playwright.async_api import async_playwright
from urllib.parse import urljoin
import csv
import os

class SuperteamBountyScraper:
    def __init__(self, json_file='superteam_bounties.json'):
        self.json_file = json_file
        self.base_url = 'https://earn.superteam.fun/listings/'
        self.xpath = '//*[@id="__next"]/div/div[4]/div/div/div[1]/div[2]/div[2]/div[1]/div/div/div/div'
        self.results = []
        self.progress_file = 'scraping_progress.json'
        
    def load_bounties(self):
        """Load bounty data from JSON file"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: {self.json_file} not found")
            return []
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {self.json_file}")
            return []
    
    def load_progress(self):
        """Load previous progress if exists"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {'completed_slugs': [], 'results': []}
        return {'completed_slugs': [], 'results': []}
    
    def save_progress(self, completed_slugs, results):
        """Save current progress"""
        progress = {
            'completed_slugs': completed_slugs,
            'results': results
        }
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
    
    async def scrape_bounty_description(self, page, slug, bounty_data):
        """Scrape description for a single bounty"""
        url = urljoin(self.base_url, slug)
        
        try:
            print(f"Scraping: {url}")
            
            # Navigate to the page
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for the content to load
            await page.wait_for_timeout(2000)
            
            # Try to find the description element using the XPath
            try:
                # Convert XPath to CSS selector or use evaluate
                description_element = await page.query_selector('xpath=' + self.xpath)
                
                if description_element:
                    description = await description_element.inner_text()
                    description = description.strip()
                else:
                    # Fallback: try to find description in common locations
                    fallback_selectors = [
                        '[data-testid="description"]',
                        '.description',
                        '[class*="description"]',
                        '[class*="content"]',
                        'main div div div div div div div'
                    ]
                    
                    description = None
                    for selector in fallback_selectors:
                        element = await page.query_selector(selector)
                        if element:
                            text = await element.inner_text()
                            if text and len(text.strip()) > 50:  # Reasonable description length
                                description = text.strip()
                                break
                    
                    if not description:
                        description = "Description not found"
                        print(f"  Warning: Could not find description for {slug}")
            
            except Exception as e:
                description = f"Error extracting description: {str(e)}"
                print(f"  Error extracting description for {slug}: {e}")
            
            # Prepare result
            result = {
                'id': bounty_data.get('id', ''),
                'title': bounty_data.get('title', ''),
                'slug': slug,
                'url': url,
                'description': description,
                'reward_amount': bounty_data.get('rewardAmount'),
                'token': bounty_data.get('token', ''),
                'deadline': bounty_data.get('deadline', ''),
                'sponsor': bounty_data.get('sponsor', {}).get('name', ''),
                'status': bounty_data.get('status', '')
            }
            
            print(f"  ✓ Successfully scraped {slug}")
            return result
            
        except Exception as e:
            print(f"  ✗ Error scraping {slug}: {e}")
            return {
                'id': bounty_data.get('id', ''),
                'title': bounty_data.get('title', ''),
                'slug': slug,
                'url': url,
                'description': f"Error: {str(e)}",
                'reward_amount': bounty_data.get('rewardAmount'),
                'token': bounty_data.get('token', ''),
                'deadline': bounty_data.get('deadline', ''),
                'sponsor': bounty_data.get('sponsor', {}).get('name', ''),
                'status': bounty_data.get('status', '')
            }
    
    async def scrape_all_bounties(self, max_concurrent=3, delay_between_requests=1):
        """Scrape descriptions for all bounties with concurrency control"""
        bounties = self.load_bounties()
        if not bounties:
            print("No bounties to scrape")
            return
        
        # Load previous progress
        progress = self.load_progress()
        completed_slugs = set(progress['completed_slugs'])
        self.results = progress['results']
        
        # Filter out already completed bounties
        remaining_bounties = [
            bounty for bounty in bounties 
            if bounty.get('slug') not in completed_slugs
        ]
        
        if not remaining_bounties:
            print("All bounties already scraped!")
            return
        
        print(f"Found {len(remaining_bounties)} bounties to scrape (out of {len(bounties)} total)")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,  # Set to False to see the browser
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                # Create browser context
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                # Process bounties in batches
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def scrape_with_semaphore(bounty):
                    async with semaphore:
                        page = await context.new_page()
                        try:
                            result = await self.scrape_bounty_description(page, bounty['slug'], bounty)
                            
                            # Add to results and save progress
                            self.results.append(result)
                            completed_slugs.add(bounty['slug'])
                            self.save_progress(list(completed_slugs), self.results)
                            
                            # Rate limiting
                            await asyncio.sleep(delay_between_requests)
                            
                            return result
                        finally:
                            await page.close()
                
                # Create tasks for all remaining bounties
                tasks = [scrape_with_semaphore(bounty) for bounty in remaining_bounties]
                
                # Execute tasks
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                print(f"\n✓ Completed scraping {len(results)} bounties")
                
            finally:
                await browser.close()
        
        # Save final results
        self.save_results()
        print(f"\n🎉 Scraping completed! Results saved to multiple formats.")
    
    def save_results(self):
        """Save results in multiple formats"""
        if not self.results:
            print("No results to save")
            return
        
        # Save as JSON
        with open('bounty_descriptions.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Save as CSV
        with open('bounty_descriptions.csv', 'w', newline='', encoding='utf-8') as f:
            if self.results:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)
        
        # Save as text file with URLs and descriptions
        with open('bounty_descriptions.txt', 'w', encoding='utf-8') as f:
            for result in self.results:
                f.write(f"Title: {result['title']}\n")
                f.write(f"URL: {result['url']}\n")
                f.write(f"Reward: {result['reward_amount']} {result['token']}\n")
                f.write(f"Sponsor: {result['sponsor']}\n")
                f.write(f"Description: {result['description']}\n")
                f.write("-" * 80 + "\n\n")
        
        print(f"Results saved to:")
        print(f"  - bounty_descriptions.json ({len(self.results)} entries)")
        print(f"  - bounty_descriptions.csv")
        print(f"  - bounty_descriptions.txt")

# Main execution
async def main():
    scraper = SuperteamBountyScraper()
    
    # Scrape with 2 concurrent browsers and 1.5 second delay between requests
    await scraper.scrape_all_bounties(max_concurrent=2, delay_between_requests=1.5)

if __name__ == "__main__":
    asyncio.run(main())