import json
import asyncio
import time
from playwright.async_api import async_playwright
from urllib.parse import urljoin
import csv
import os

class ImprovedSuperteamBountyScraper:
    def __init__(self, json_file='data/superteam_bounties.json'):
        self.json_file = json_file
        self.base_url = 'https://earn.superteam.fun/listing/'
        self.results = []
        self.progress_file = 'output/scraping_progress.json'
        
        # Multiple selector strategies to try
        self.description_selectors = [
            # Try common description containers
            '[data-testid*="description"]',
            '[class*="description"]',
            '[class*="content"]',
            '[class*="detail"]',
            '[class*="body"]',
            
            # Try semantic HTML elements
            'main p',
            'article p',
            'section p',
            
            # Try by text content patterns
            'div:has-text("Description")',
            'div:has-text("About")',
            'div:has-text("Details")',
            
            # Generic content areas
            'main div div div div div p',
            'main div div div div p',
            '[role="main"] p',
            
            # Fallback to any substantial text content
            'main div:has(p)',
            'div[class*="container"] p'
        ]
    
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
    
    async def debug_page_structure(self, page, slug):
        """Debug function to understand page structure"""
        print(f"\n🔍 Debugging page structure for: {slug}")
        
        # Get page title
        title = await page.title()
        print(f"  Page title: {title}")
        
        # Check if page loaded properly
        main_content = await page.query_selector('main')
        if main_content:
            print("  ✓ Main content area found")
        else:
            print("  ✗ No main content area found")
        
        # Look for common content indicators
        indicators = ['p', 'div[class*="content"]', '[data-testid]', 'article']
        for indicator in indicators:
            elements = await page.query_selector_all(indicator)
            if elements:
                print(f"  Found {len(elements)} {indicator} elements")
        
        # Get all text content to see what's available
        body_text = await page.evaluate('() => document.body.innerText')
        if body_text:
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            print(f"  Total text lines: {len(lines)}")
            if len(lines) > 5:
                print(f"  Sample text: {lines[5][:100]}...")
    
    async def extract_description_smart(self, page, slug):
        """Smart description extraction with multiple strategies"""
        description = None
        
        # Strategy 1: Try predefined selectors
        for selector in self.description_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    for element in elements:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 30:  # Reasonable description length
                            description = text.strip()
                            print(f"  ✓ Found description using selector: {selector}")
                            break
                    if description:
                        break
            except Exception as e:
                continue
        
        # Strategy 2: Look for paragraphs with substantial content
        if not description:
            try:
                paragraphs = await page.query_selector_all('p')
                for p in paragraphs:
                    text = await p.inner_text()
                    if text and len(text.strip()) > 50:
                        description = text.strip()
                        print(f"  ✓ Found description in paragraph")
                        break
            except Exception as e:
                pass
        
        # Strategy 3: Extract from main content area
        if not description:
            try:
                main = await page.query_selector('main')
                if main:
                    # Get all text from main, then try to find description-like content
                    main_text = await main.inner_text()
                    if main_text:
                        lines = [line.strip() for line in main_text.split('\n') if line.strip()]
                        # Look for longer lines that might be descriptions
                        for line in lines:
                            if len(line) > 100 and not line.startswith(('$', 'USDC', 'Deadline')):
                                description = line
                                print(f"  ✓ Found description in main content")
                                break
            except Exception as e:
                pass
        
        # Strategy 4: Use JavaScript to find content
        if not description:
            try:
                description = await page.evaluate('''
                    () => {
                        // Look for elements with substantial text content
                        const allDivs = document.querySelectorAll('div');
                        for (let div of allDivs) {
                            const text = div.innerText;
                            if (text && text.length > 100 && text.length < 2000) {
                                // Check if it's likely a description (not navigation, etc.)
                                if (!text.includes('Sign in') && !text.includes('Menu') && 
                                    !text.includes('Navigation') && text.includes(' ')) {
                                    return text.trim();
                                }
                            }
                        }
                        return null;
                    }
                ''')
                if description:
                    print(f"  ✓ Found description using JavaScript extraction")
            except Exception as e:
                pass
        
        return description or "Description not found"
    
    async def scrape_bounty_description(self, page, slug, bounty_data, debug=False):
        """Scrape description for a single bounty with improved extraction"""
        url = urljoin(self.base_url, slug)
        
        try:
            print(f"\nScraping: {url}")
            
            # Navigate to the page
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for content to load
            await page.wait_for_timeout(3000)
            
            # Debug page structure if requested
            if debug:
                await self.debug_page_structure(page, slug)
            
            # Extract description using smart strategies
            description = await self.extract_description_smart(page, slug)
            
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
            
            if description != "Description not found":
                print(f"  ✓ Successfully scraped {slug}")
            else:
                print(f"  ⚠️  Could not find description for {slug}")
            
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
    
    async def scrape_sample_bounties(self, sample_size=5, debug=True):
        """Scrape a small sample first to test selectors"""
        bounties = self.load_bounties()
        if not bounties:
            print("No bounties to scrape")
            return
        
        # Take a sample
        sample_bounties = bounties[:sample_size]
        print(f"Testing with {len(sample_bounties)} sample bounties...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Show browser for debugging
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                for bounty in sample_bounties:
                    result = await self.scrape_bounty_description(page, bounty['slug'], bounty, debug=debug)
                    self.results.append(result)
                    
                    # Small delay between requests
                    await asyncio.sleep(2)
                
            finally:
                await browser.close()
        
        # Save sample results
        self.save_results(filename_suffix='_sample')
        print(f"\n🎉 Sample scraping completed! Check the results.")
    
    def save_results(self, filename_suffix=''):
        """Save results in multiple formats"""
        if not self.results:
            print("No results to save")
            return
        
        # Save as JSON
        # Around line 285-289, update the save methods:
        with open(f'output/bounty_descriptions{filename_suffix}.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to:")
        with open(f'output/bounty_descriptions{filename_suffix}.txt', 'w', encoding='utf-8') as f:
            for result in self.results:
                f.write(f"Title: {result['title']}\n")
                f.write(f"URL: {result['url']}\n")
                f.write(f"Reward: {result['reward_amount']} {result['token']}\n")
                f.write(f"Sponsor: {result['sponsor']}\n")
                f.write(f"Description: {result['description']}\n")
                f.write("-" * 80 + "\n\n")
        
        print(f"Results saved to:")
        print(f"  - bounty_descriptions{filename_suffix}.json ({len(self.results)} entries)")
        print(f"  - bounty_descriptions{filename_suffix}.txt")

# Main execution
async def main():
    scraper = ImprovedSuperteamBountyScraper()
    
    # First, test with a small sample
    await scraper.scrape_sample_bounties(sample_size=3, debug=True)

if __name__ == "__main__":
    asyncio.run(main())