import json
import asyncio
import time
from playwright.async_api import async_playwright
from urllib.parse import urljoin
import csv
import os

class ImprovedSuperteamBountyScraper:
    def __init__(self, links_file='data/bounty_links.txt', json_file='data/superteam_bounties.json'):
        self.links_file = links_file
        self.json_file = json_file
        self.base_url = 'https://earn.superteam.fun/listing/'
        self.results = []
        self.progress_file = 'output/scraping_progress.json'
        self.bounty_data_cache = {}  # Cache for API data
        self.processed_file = 'data/processed_bounties.json'
        self.results_file = 'output/bounty_descriptions.json'
        
        # Add the missing description_selectors attribute
        self.description_selectors = [
            'div[class*="description"]',
            'div[class*="content"]',
            'div[data-testid*="description"]',
            'div[class*="body"]',
            'div[class*="details"]',
            '.description',
            '.content',
            '.bounty-description',
            '.listing-description',
            'article',
            'section[class*="description"]',
            'div[class*="text"]'
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
    
    async def extract_country_restriction(self, page, url):
        """Extract country restriction from the page"""
        try:
            # Try the exact XPath first
            try:
                element = await page.wait_for_selector(f'xpath={self.country_xpath}', timeout=5000)
                if element:
                    country_text = await element.text_content()
                    country_restriction = country_text.strip() if country_text else None
                    if country_restriction:
                        print(f"  ✓ Found country restriction: {country_restriction}")
                        return country_restriction
            except Exception:
                pass
            
            # Fallback: look for spans with country codes
            try:
                # Look for spans that might contain country codes
                country_elements = await page.query_selector_all('span.text-slate-400')
                for elem in country_elements:
                    text = await elem.text_content()
                    if text and len(text.strip()) == 2 and text.strip().isupper():
                        country_restriction = text.strip()
                        print(f"  ✓ Found country restriction (fallback): {country_restriction}")
                        return country_restriction
                
                # If still not found, look for common country code patterns
                all_spans = await page.query_selector_all('span')
                for span in all_spans:
                    text = await span.text_content()
                    if text and text.strip() in ['IE', 'IN', 'VN', 'US', 'UK', 'CA', 'AU', 'DE', 'FR', 'GLOBAL']:
                        country_restriction = text.strip()
                        print(f"  ✓ Found country restriction (pattern): {country_restriction}")
                        return country_restriction
                        
            except Exception:
                pass
            
            # If no country restriction found, check if it might be global
            page_content = await page.content()
            if 'global' in page_content.lower() or not any(cc in page_content for cc in ['IE', 'IN', 'VN']):
                print(f"  ✓ Assuming GLOBAL restriction")
                return 'GLOBAL'
            
            print(f"  ⚠️  No country restriction found")
            return None
            
        except Exception as e:
            print(f"  ✗ Error extracting country restriction: {e}")
            return None
    
    async def scrape_bounty_from_url(self, page, url, debug=False):
        """Scrape description and country restriction for a single bounty from URL"""
        slug = self.extract_slug_from_url(url)
        
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
            
            # Extract country restriction
            country_restriction = await self.extract_country_restriction(page, url)
            
            # Extract basic info from the page
            title = await page.title() or slug.replace('-', ' ').title()
            
            # Get reward amount from cached API data first
            reward_amount = None
            token = ""
            deadline = ""
            sponsor = ""
            
            if slug in self.bounty_data_cache:
                api_data = self.bounty_data_cache[slug]
                reward_amount = api_data.get('rewardAmount')
                token = api_data.get('token', '')
                deadline = api_data.get('deadline', '')
                sponsor = api_data.get('sponsor', {}).get('name', '') if api_data.get('sponsor') else ''
                # Use API title if available
                if api_data.get('title'):
                    title = api_data['title']
            
            # Fallback: try to extract from page if not in cache
            if reward_amount is None:
                page_text = await page.evaluate('() => document.body.innerText')
                reward_amount = self.extract_reward_amount_from_page(page_text)
            
            # Prepare result with country restriction included
            result = {
                'title': title,
                'slug': slug,
                'url': url,
                'description': description,
                'country_restriction': country_restriction,  # New field
                'reward_amount': reward_amount,
                'token': token,
                'deadline': deadline,  # Now uses API data
                'sponsor': sponsor,    # Now uses API data
                'status': 'active'
            }
            
            success_msg = f"  ✓ Successfully scraped {slug}"
            if country_restriction:
                success_msg += f" (Country: {country_restriction})"
            print(success_msg)
            
            return result
            
        except Exception as e:
            print(f"  ✗ Error scraping {url}: {e}")
            return {
                'title': slug.replace('-', ' ').title(),
                'slug': slug,
                'url': url,
                'description': f"Error: {str(e)}",
                'country_restriction': None,
                'reward_amount': None,
                'token': '',
                'deadline': '',
                'sponsor': '',
                'status': 'error'
            }

    async def scrape_all_bounties(self, debug=False):
        """Scrape all bounties from the links file"""
        # Load bounty data cache first
        self.load_bounty_data_cache()
        
        links = self.load_bounty_links()
        if not links:
            print("No bounty links to scrape")
            return
        
        print(f"Found {len(links)} bounty links to scrape...")
        
        # Load previous progress
        progress = self.load_progress()
        completed_urls = set(result.get('url', '') for result in progress.get('results', []))
        self.results = progress.get('results', [])
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,  # Set to False for debugging
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                for i, url in enumerate(links, 1):
                    # Skip if already completed
                    if url in completed_urls:
                        print(f"[{i}/{len(links)}] Skipping {url} (already completed)")
                        continue
                    
                    print(f"[{i}/{len(links)}] Processing {url}")
                    result = await self.scrape_bounty_from_url(page, url, debug=debug)
                    self.results.append(result)
                    
                    # Save progress every 5 bounties
                    if i % 5 == 0:
                        completed_urls_list = [r['url'] for r in self.results]
                        self.save_progress(completed_urls_list, self.results)
                        print(f"Progress saved ({i}/{len(links)} completed)")
                    
                    # Small delay between requests to be respectful
                    await asyncio.sleep(2)
                
            finally:
                await browser.close()
        
        # Final save
        completed_urls_list = [r['url'] for r in self.results]
        self.save_progress(completed_urls_list, self.results)
        
        # Save final results
        self.save_results()
        print(f"\n🎉 Scraping completed! Processed {len(self.results)} bounties.")

    def save_results(self, filename_suffix=''):
        """Save results in JSON format with country restrictions included"""
        if not self.results:
            print("No results to save")
            return
        
        # Add summary statistics including country breakdown
        summary = {
            'total_bounties': len(self.results),
            'successful_scrapes': len([r for r in self.results if r['description'] != 'Description not found' and not r['description'].startswith('Error:')]),
            'country_breakdown': {},
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Count country restrictions
        for result in self.results:
            if result.get('country_restriction'):
                country = result['country_restriction']
                summary['country_breakdown'][country] = summary['country_breakdown'].get(country, 0) + 1
        
        # Save as JSON with summary
        output_data = {
            'summary': summary,
            'results': self.results
        }
        
        with open(f'output/bounty_descriptions{filename_suffix}.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to:")
        print(f"  - bounty_descriptions{filename_suffix}.json ({len(self.results)} entries)")
        print(f"\nCountry breakdown:")
        for country, count in summary['country_breakdown'].items():
            print(f"  {country}: {count} bounties")

# Add these methods to the ImprovedSuperteamBountyScraper class (around line 520, before the main() function)

    def load_processed_bounties(self):
        """Load previously processed bounty IDs"""
        try:
            with open(self.processed_file, 'r') as f:
                return set(json.load(f))
        except FileNotFoundError:
            return set()
    
    def save_processed_bounties(self, bounty_ids):
        """Save processed bounty IDs"""
        with open(self.processed_file, 'w') as f:
            json.dump(list(bounty_ids), f)
    
    def load_existing_results(self):
        """Load existing results from output file"""
        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    async def scrape_new_bounties_only(self):
        """Scrape only new bounties that haven't been processed yet"""
        print("🚀 Starting incremental bounty scraping...")
        
        # Load processed bounties and existing results
        processed_ids = self.load_processed_bounties()
        existing_results = self.load_existing_results()
        
        # Load bounty data and filter for new ones
        all_bounties = self.load_bounties()
        new_bounties = [b for b in all_bounties if b['id'] not in processed_ids]
        
        if not new_bounties:
            print("No new bounties to process.")
            return
        
        print(f"Found {len(new_bounties)} new bounties to scrape")
        
        # Load bounty data cache
        self.load_bounty_data_cache()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            new_results = []
            new_processed_ids = set()
            
            for i, bounty in enumerate(new_bounties, 1):
                slug = bounty['slug']
                url = f"https://earn.superteam.fun/listing/{slug}"
                
                print(f"\n[{i}/{len(new_bounties)}] Processing: {slug}")
                
                try:
                    result = await self.scrape_bounty_from_url(page, url)
                    if result:
                        new_results.append(result)
                        new_processed_ids.add(bounty['id'])
                        print(f"  ✅ Successfully scraped: {slug}")
                    else:
                        print(f"  ⚠️  No content found for: {slug}")
                        
                except Exception as e:
                    print(f"  ❌ Error scraping {slug}: {str(e)}")
                
                # Small delay between requests
                await asyncio.sleep(1)
            
            await browser.close()
        
        # Update results and processed IDs
        if new_results:
            all_results = existing_results + new_results
            
            # Save updated results
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            
            # Update processed bounties
            all_processed_ids = processed_ids.union(new_processed_ids)
            self.save_processed_bounties(all_processed_ids)
            
            print(f"\n✅ Successfully processed {len(new_results)} new bounties")
            print(f"📁 Results saved to: {self.results_file}")
            print(f"📊 Total bounties in database: {len(all_results)}")
        else:
            print("\n⚠️  No new results to save")

    def load_bounty_links(self):
        """Load bounty URLs from text file"""
        try:
            with open(self.links_file, 'r', encoding='utf-8') as f:
                links = [line.strip() for line in f if line.strip()]
            return links
        except FileNotFoundError:
            print(f"Error: {self.links_file} not found")
            return []
    
    def extract_slug_from_url(self, url):
        """Extract slug from full URL"""
        if '/listing/' in url:
            return url.split('/listing/')[-1]
        return url
    
    def load_bounty_data_cache(self):
        """Load and cache bounty data from API JSON for quick lookup"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                bounties = json.load(f)
                # Create a lookup cache by slug
                for bounty in bounties:
                    self.bounty_data_cache[bounty['slug']] = bounty
                print(f"Loaded {len(bounties)} bounties into cache")
        except FileNotFoundError:
            print(f"Warning: {self.json_file} not found. Reward amounts will be extracted from pages.")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {self.json_file}")
    
    def extract_reward_amount_from_page(self, page_text):
        """Extract numeric reward amount from page content as fallback"""
        import re
        
        # Look for patterns like "500 USDC", "$500", "2,000 USDC"
        patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*(?:USDC|SOL|sUSD|JUP)',
            r'\$(\d{1,3}(?:,\d{3})*)',
            r'Total Prizes[\s\S]*?(\d{1,3}(?:,\d{3})*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                # Return the first numeric match, removing commas
                return int(matches[0].replace(',', ''))
        
        return None

# Main execution
async def main():
    scraper = ImprovedSuperteamBountyScraper()
    
    # Scrape all bounties from bounty_links.txt
    await scraper.scrape_all_bounties(debug=False)

if __name__ == "__main__":
    asyncio.run(main())