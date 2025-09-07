import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from urllib.parse import urlparse
import time

class CountryRestrictionScraper:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.output_dir = self.base_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # XPath for country restriction element
        self.country_xpath = '//*[@id="__next"]/div/div[4]/div/div/div[1]/div[1]/div[2]/div/button/div/span'
        
    def load_bounty_links(self):
        """Load bounty URLs from the text file"""
        links_file = self.data_dir / "bounty_links.txt"
        if not links_file.exists():
            raise FileNotFoundError(f"Bounty links file not found: {links_file}")
            
        with open(links_file, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]
            
        print(f"Loaded {len(links)} bounty links")
        return links
    
    def extract_slug_from_url(self, url):
        """Extract the bounty slug from URL for identification"""
        try:
            path = urlparse(url).path
            return path.split('/')[-1] if path.split('/')[-1] else path.split('/')[-2]
        except:
            return url
    
    async def scrape_country_restriction(self, page, url):
        """Scrape country restriction from a single bounty page"""
        try:
            print(f"Scraping: {url}")
            
            # Navigate to the page
            response = await page.goto(url, wait_until='networkidle', timeout=30000)
            
            if response.status != 200:
                print(f"Warning: HTTP {response.status} for {url}")
                return {
                    'url': url,
                    'slug': self.extract_slug_from_url(url),
                    'country_restriction': None,
                    'error': f'HTTP {response.status}',
                    'status': 'failed'
                }
            
            # Wait a bit for dynamic content to load
            await page.wait_for_timeout(2000)
            
            # Try to find the country restriction element
            country_restriction = None
            try:
                # First try the exact XPath
                element = await page.wait_for_selector(f'xpath={self.country_xpath}', timeout=5000)
                if element:
                    country_text = await element.text_content()
                    country_restriction = country_text.strip() if country_text else None
                    
            except Exception as xpath_error:
                print(f"XPath failed for {url}, trying alternative selectors...")
                
                # Fallback: look for spans with country codes
                try:
                    # Look for spans that might contain country codes
                    country_elements = await page.query_selector_all('span.text-slate-400')
                    for elem in country_elements:
                        text = await elem.text_content()
                        if text and len(text.strip()) == 2 and text.strip().isupper():
                            country_restriction = text.strip()
                            break
                    
                    # If still not found, look for common country code patterns
                    if not country_restriction:
                        all_spans = await page.query_selector_all('span')
                        for span in all_spans:
                            text = await span.text_content()
                            if text and text.strip() in ['IE', 'IN', 'VN', 'US', 'UK', 'CA', 'AU', 'DE', 'FR', 'GLOBAL']:
                                country_restriction = text.strip()
                                break
                                
                except Exception as fallback_error:
                    print(f"Fallback selectors also failed: {fallback_error}")
            
            # If no country restriction found, it might be global
            if not country_restriction:
                # Check if there's any indication this is a global bounty
                page_content = await page.content()
                if 'global' in page_content.lower() or not any(cc in page_content for cc in ['IE', 'IN', 'VN']):
                    country_restriction = 'GLOBAL'
            
            result = {
                'url': url,
                'slug': self.extract_slug_from_url(url),
                'country_restriction': country_restriction,
                'error': None,
                'status': 'success' if country_restriction else 'no_restriction_found'
            }
            
            print(f"✓ {url} -> {country_restriction or 'No restriction found'}")
            return result
            
        except Exception as e:
            print(f"✗ Error scraping {url}: {str(e)}")
            return {
                'url': url,
                'slug': self.extract_slug_from_url(url),
                'country_restriction': None,
                'error': str(e),
                'status': 'failed'
            }
    
    async def scrape_all_restrictions(self):
        """Scrape country restrictions from all bounty links"""
        links = self.load_bounty_links()
        results = []
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                total_links = len(links)
                for i, url in enumerate(links, 1):
                    print(f"\nProgress: {i}/{total_links}")
                    
                    result = await self.scrape_country_restriction(page, url)
                    results.append(result)
                    
                    # Small delay between requests
                    await asyncio.sleep(1)
                    
            finally:
                await browser.close()
        
        return results
    
    def save_results(self, results):
        """Save results to JSON file"""
        output_file = self.output_dir / "country_restrictions_test.json"
        
        # Add summary statistics
        summary = {
            'total_bounties': len(results),
            'successful_scrapes': len([r for r in results if r['status'] == 'success']),
            'failed_scrapes': len([r for r in results if r['status'] == 'failed']),
            'no_restriction_found': len([r for r in results if r['status'] == 'no_restriction_found']),
            'country_breakdown': {}
        }
        
        # Count country restrictions
        for result in results:
            if result['country_restriction']:
                country = result['country_restriction']
                summary['country_breakdown'][country] = summary['country_breakdown'].get(country, 0) + 1
        
        output_data = {
            'summary': summary,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'results': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Results saved to: {output_file}")
        print(f"Summary:")
        print(f"  Total bounties: {summary['total_bounties']}")
        print(f"  Successful: {summary['successful_scrapes']}")
        print(f"  Failed: {summary['failed_scrapes']}")
        print(f"  No restriction found: {summary['no_restriction_found']}")
        print(f"  Country breakdown: {summary['country_breakdown']}")

async def main():
    scraper = CountryRestrictionScraper()
    print("Starting country restriction scraping...")
    
    results = await scraper.scrape_all_restrictions()
    scraper.save_results(results)
    
    print("\nScraping completed!")

if __name__ == "__main__":
    asyncio.run(main())