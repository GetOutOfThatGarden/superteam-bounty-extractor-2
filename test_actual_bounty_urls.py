import asyncio
from playwright.async_api import async_playwright
import json
import csv
from datetime import datetime

class ActualURLTester:
    def __init__(self, urls_file='bounty_links.txt'):
        self.urls_file = urls_file
        self.results = []
        self.active_urls = []
        self.expired_urls = []
        
    def load_urls(self):
        """Load URLs from the bounty_links.txt file"""
        try:
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(urls)} URLs from {self.urls_file}")
            return urls
        except FileNotFoundError:
            print(f"Error: {self.urls_file} not found")
            return []
    
    async def test_url_status(self, page, url):
        """Test if a URL is active and contains bounty content"""
        try:
            print(f"Testing: {url}")
            
            # Navigate to the page
            response = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            
            # Check response status
            if response.status == 404:
                print(f"  ✗ 404 - Not found")
                return False, "404 - Not found", ""
            
            # Wait for content to load
            await page.wait_for_timeout(2000)
            
            # Check page title
            title = await page.title()
            if "Not Found" in title or "404" in title:
                print(f"  ✗ Not Found page (title: {title})")
                return False, "Not Found page", title
            
            # Get page content
            page_text = await page.evaluate('() => document.body.innerText')
            
            # Check for "Nothing Found" or error messages
            if "Nothing Found" in page_text or "Sorry, we couldn't find" in page_text:
                print(f"  ✗ Content indicates 404")
                return False, "Content not found", title
            
            # Check for bounty-specific indicators
            bounty_indicators = [
                'Apply Now',
                'Deadline',
                'Reward',
                'USDC',
                'Sponsor',
                'Description',
                'Requirements',
                'Submission'
            ]
            
            found_indicators = []
            for indicator in bounty_indicators:
                if indicator in page_text:
                    found_indicators.append(indicator)
            
            if len(found_indicators) >= 3:  # At least 3 bounty indicators
                print(f"  ✓ Active bounty (found: {', '.join(found_indicators)})")
                return True, "Active", title
            else:
                print(f"  ⚠️  Suspicious content (found: {', '.join(found_indicators)})")
                return False, f"Insufficient indicators ({len(found_indicators)}/3)", title
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False, f"Error: {str(e)}", ""
    
    async def extract_bounty_info(self, page, url):
        """Extract basic bounty information from an active page"""
        try:
            # Get title from page
            page_title = await page.title()
            
            # Try to extract bounty title from page content
            bounty_title = await page.evaluate('''
                () => {
                    // Look for h1 or main heading
                    const h1 = document.querySelector('h1');
                    if (h1 && h1.innerText.trim()) {
                        return h1.innerText.trim();
                    }
                    
                    // Look for title in meta tags
                    const titleMeta = document.querySelector('meta[property="og:title"]');
                    if (titleMeta) {
                        return titleMeta.content;
                    }
                    
                    // Fallback to page title
                    return document.title.replace(' | Superteam Earn', '');
                }
            ''')
            
            # Try to extract reward information
            reward_info = await page.evaluate('''
                () => {
                    const text = document.body.innerText;
                    
                    // Look for USDC amounts
                    const usdcMatch = text.match(/(\d+(?:,\d+)*(?:\.\d+)?)\s*USDC/i);
                    if (usdcMatch) {
                        return usdcMatch[0];
                    }
                    
                    // Look for other token amounts
                    const tokenMatch = text.match(/(\d+(?:,\d+)*(?:\.\d+)?)\s*([A-Z]{2,10})/i);
                    if (tokenMatch) {
                        return tokenMatch[0];
                    }
                    
                    return 'Reward not found';
                }
            ''')
            
            # Try to extract description
            description = await self.extract_description_smart(page)
            
            return {
                'url': url,
                'page_title': page_title,
                'bounty_title': bounty_title,
                'reward': reward_info,
                'description': description,
                'status': 'active'
            }
            
        except Exception as e:
            return {
                'url': url,
                'page_title': 'Error',
                'bounty_title': 'Error extracting title',
                'reward': 'Error',
                'description': f'Error extracting info: {str(e)}',
                'status': 'error'
            }
    
    async def extract_description_smart(self, page):
        """Smart description extraction with multiple strategies"""
        description_selectors = [
            # Common description patterns
            '[data-testid*="description"]',
            '[class*="description"]',
            '[class*="content"]',
            '[class*="detail"]',
            '[class*="body"]',
            
            # Semantic elements
            'main p',
            'article p',
            'section p',
            
            # Generic content areas
            'main div div div p',
            '[role="main"] p'
        ]
        
        # Try each selector
        for selector in description_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.inner_text()
                    if text and len(text.strip()) > 50:
                        # Avoid navigation/header text
                        if not any(nav_text in text for nav_text in ['Sign Up', 'Login', 'Menu', 'Navigation', 'Footer', '© 2025']):
                            return text.strip()[:500] + ('...' if len(text.strip()) > 500 else '')
            except Exception:
                continue
        
        # Fallback: look for substantial paragraph content
        try:
            paragraphs = await page.query_selector_all('p')
            for p in paragraphs:
                text = await p.inner_text()
                if text and len(text.strip()) > 100:
                    if not any(skip in text for skip in ['Sign Up', 'Login', 'Menu', 'Footer', '© 2025']):
                        return text.strip()[:500] + ('...' if len(text.strip()) > 500 else '')
        except Exception:
            pass
        
        return "Description not found"
    
    async def test_all_urls(self, max_concurrent=3, sample_size=None):
        """Test all URLs from the file"""
        urls = self.load_urls()
        if not urls:
            print("No URLs to test")
            return
        
        # Optionally test only a sample
        if sample_size:
            urls = urls[:sample_size]
            print(f"Testing sample of {len(urls)} URLs...")
        else:
            print(f"Testing all {len(urls)} URLs...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,  # Set to False to see browser
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                # Test URLs with concurrency control
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def test_single_url(url):
                    async with semaphore:
                        page = await context.new_page()
                        try:
                            is_active, status, title = await self.test_url_status(page, url)
                            
                            if is_active:
                                # Extract detailed info for active bounties
                                bounty_info = await self.extract_bounty_info(page, url)
                                self.results.append(bounty_info)
                                self.active_urls.append(url)
                            else:
                                self.expired_urls.append({
                                    'url': url,
                                    'status': status,
                                    'title': title
                                })
                            
                            # Rate limiting
                            await asyncio.sleep(1)
                            
                        finally:
                            await page.close()
                
                # Test all URLs
                tasks = [test_single_url(url) for url in urls]
                await asyncio.gather(*tasks, return_exceptions=True)
                
            finally:
                await browser.close()
        
        # Save results
        self.save_results()
        
        print(f"\n📊 Test Results:")
        print(f"  ✓ Active bounties: {len(self.active_urls)}")
        print(f"  ✗ Expired/invalid: {len(self.expired_urls)}")
        print(f"  📈 Success rate: {len(self.active_urls)}/{len(urls)} ({len(self.active_urls)/len(urls)*100:.1f}%)")
        
        if self.active_urls:
            print(f"\n🎯 Active bounty URLs:")
            for url in self.active_urls[:5]:  # Show first 5
                print(f"  - {url}")
            if len(self.active_urls) > 5:
                print(f"  ... and {len(self.active_urls) - 5} more")
    
    def save_results(self):
        """Save test results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save active bounties with details
        if self.results:
            with open(f'active_bounties_tested_{timestamp}.json', 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            # Save as readable text
            with open(f'active_bounties_tested_{timestamp}.txt', 'w', encoding='utf-8') as f:
                for result in self.results:
                    f.write(f"Title: {result['bounty_title']}\n")
                    f.write(f"URL: {result['url']}\n")
                    f.write(f"Reward: {result['reward']}\n")
                    f.write(f"Description: {result['description']}\n")
                    f.write("-" * 80 + "\n\n")
        
        # Save expired URLs
        if self.expired_urls:
            with open(f'expired_bounties_{timestamp}.json', 'w', encoding='utf-8') as f:
                json.dump(self.expired_urls, f, indent=2, ensure_ascii=False)
        
        # Save active URLs list
        if self.active_urls:
            with open(f'confirmed_active_urls_{timestamp}.txt', 'w', encoding='utf-8') as f:
                for url in self.active_urls:
                    f.write(f"{url}\n")
        
        print(f"\nResults saved:")
        if self.results:
            print(f"  - active_bounties_tested_{timestamp}.json ({len(self.results)} entries)")
            print(f"  - active_bounties_tested_{timestamp}.txt")
        if self.expired_urls:
            print(f"  - expired_bounties_{timestamp}.json ({len(self.expired_urls)} entries)")
        if self.active_urls:
            print(f"  - confirmed_active_urls_{timestamp}.txt ({len(self.active_urls)} URLs)")

# Main execution
async def main():
    tester = ActualURLTester()
    
    # Test with a small sample first (5 URLs)
    print("🧪 Testing sample of 5 URLs first...")
    await tester.test_all_urls(max_concurrent=2, sample_size=5)
    
    # Ask if user wants to continue with all URLs
    if tester.active_urls:
        print(f"\n✅ Found {len(tester.active_urls)} active URLs in sample!")
        print("\nTo test all URLs, run:")
        print("python test_actual_bounty_urls.py --all")
    else:
        print("\n❌ No active URLs found in sample. All tested URLs appear to be expired.")

# Alternative: test all URLs
async def test_all():
    tester = ActualURLTester()
    await tester.test_all_urls(max_concurrent=3)  # Test all URLs

if __name__ == "__main__":
    import sys
    if '--all' in sys.argv:
        asyncio.run(test_all())
    else:
        asyncio.run(main())