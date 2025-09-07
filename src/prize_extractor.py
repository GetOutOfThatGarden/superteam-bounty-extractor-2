import json
import asyncio
from playwright.async_api import async_playwright
import re

class PrizeExtractor:
    def __init__(self):
        self.results = []
    
    async def click_view_more_buttons(self, page):
        """Click all 'View More' buttons to expand hidden prizes"""
        try:
            # Look for "View More" buttons
            view_more_buttons = await page.query_selector_all('button:has-text("View More")')
            
            if view_more_buttons:
                print(f"  Found {len(view_more_buttons)} 'View More' button(s)")
                
                for i, button in enumerate(view_more_buttons):
                    try:
                        # Check if button is visible and clickable
                        is_visible = await button.is_visible()
                        if is_visible:
                            print(f"  Clicking 'View More' button {i+1}")
                            await button.click()
                            # Wait for content to expand
                            await page.wait_for_timeout(1000)
                    except Exception as e:
                        print(f"  Could not click 'View More' button {i+1}: {e}")
            else:
                print("  No 'View More' buttons found")
                
        except Exception as e:
            print(f"  Error handling 'View More' buttons: {e}")
    
    def expand_range_positions(self, prizes):
        """Expand range positions like '5th - 10th' into individual positions"""
        expanded_prizes = []
        
        for prize in prizes:
            position = prize['position']
            amount = prize['amount']
            
            # Handle range positions like "5th - 10th", "5th–10th", etc.
            if ' - ' in position or '–' in position or ' to ' in position:
                # Extract start and end positions
                range_match = re.search(r'(\d+)(?:st|nd|rd|th)?\s*[-–]\s*(\d+)(?:st|nd|rd|th)?', position)
                if range_match:
                    start_pos = int(range_match.group(1))
                    end_pos = int(range_match.group(2))
                    
                    # Create individual positions
                    for pos in range(start_pos, end_pos + 1):
                        if pos == 1:
                            pos_suffix = "1st"
                        elif pos == 2:
                            pos_suffix = "2nd"
                        elif pos == 3:
                            pos_suffix = "3rd"
                        else:
                            pos_suffix = f"{pos}th"
                        
                        expanded_prizes.append({
                            'position': pos_suffix,
                            'amount': amount
                        })
                    
                    print(f"  Expanded '{position}' into positions {start_pos}-{end_pos}, each with {amount}")
                else:
                    # If regex fails, keep original
                    expanded_prizes.append(prize)
            else:
                # Regular position, keep as-is
                expanded_prizes.append(prize)
        
        return expanded_prizes

    async def extract_prize_breakdown(self, page):
        """Extract individual prize amounts from the prize breakdown table"""
        try:
            # First, click any "View More" buttons to expand hidden content
            await self.click_view_more_buttons(page)
            
            prize_breakdown = []
            
            # Strategy 1: Look for the specific HTML structure from the provided example
            # Target the exact structure: div.relative.flex.gap-3 containing prize info
            prize_rows = await page.query_selector_all('div.relative.flex.gap-3')
            
            for row in prize_rows:
                try:
                    # Look for amount in the structure: div.flex.gap-1 > p.ml-auto
                    amount_container = await row.query_selector('div.flex.gap-1')
                    if amount_container:
                        amount_element = await amount_container.query_selector('p.ml-auto')
                        if amount_element:
                            amount_text = await amount_element.inner_text()
                            # Handle comma-separated numbers like "1,000"
                            amount_clean = amount_text.strip().replace(',', '')
                            
                            if amount_clean.isdigit():
                                amount = int(amount_clean)
                                
                                # Look for position in the same container
                                position_element = await row.query_selector('p.mt-auto.mb-1, p:has-text("1st"), p:has-text("2nd"), p:has-text("3rd"), p:has-text("4th"), p:has-text("5th"), p:has-text("6th"), p:has-text("7th"), p:has-text("8th"), p:has-text("9th"), p:has-text("10th")')
                                
                                if position_element:
                                    position_text = await position_element.inner_text()
                                    position = position_text.strip()
                                    
                                    prize_breakdown.append({
                                        'position': position,
                                        'amount': amount
                                    })
                                    print(f"  Found prize: {position} = {amount}")
                    
                    # Also check for "+X,XXX" pattern (additional prizes)
                    plus_amount_element = await row.query_selector('p:has-text("+")')
                    if plus_amount_element:
                        plus_text = await plus_amount_element.inner_text()
                        # Extract number from "+1,000" format
                        plus_match = re.search(r'\+(\d{1,3}(?:,\d{3})*)', plus_text)
                        if plus_match:
                            additional_amount = int(plus_match.group(1).replace(',', ''))
                            prize_breakdown.append({
                                'position': 'additional',
                                'amount': additional_amount
                            })
                            print(f"  Found additional prize: +{additional_amount}")
                            
                except Exception as e:
                    print(f"  Error processing row: {e}")
                    continue
            
            # Strategy 2: More specific approach for the exact HTML structure
            if not prize_breakdown:
                try:
                    # Look for the specific pattern: amount followed by position
                    # Based on your HTML: <p class="ml-auto">1,000</p> ... <p class="mt-auto mb-1 ...">1st</p>
                    
                    # Find all amount elements first
                    amount_elements = await page.query_selector_all('p.ml-auto')
                    
                    for amount_element in amount_elements:
                        try:
                            amount_text = await amount_element.inner_text()
                            amount_clean = amount_text.strip().replace(',', '')
                            
                            if amount_clean.isdigit():
                                amount = int(amount_clean)
                                
                                # Find the corresponding position element in the same row
                                # Navigate up to the parent container and look for position
                                parent_row = await amount_element.evaluate('el => el.closest("div.relative.flex.gap-3")')
                                if parent_row:
                                    position_element = await parent_row.query_selector('p.mt-auto.mb-1, p:has-text("1st"), p:has-text("2nd"), p:has-text("3rd"), p:has-text("4th"), p:has-text("5th")')
                                    if position_element:
                                        position_text = await position_element.inner_text()
                                        position = position_text.strip()
                                        
                                        prize_breakdown.append({
                                            'position': position,
                                            'amount': amount
                                        })
                                        print(f"  Strategy 2 - Found prize: {position} = {amount}")
                        except Exception as e:
                            print(f"  Strategy 2 error: {e}")
                            continue
                            
                except Exception as e:
                    print(f"  Strategy 2 failed: {e}")
                    pass
            
            # Strategy 3: Parse page text for all prize information (fallback)
            if not prize_breakdown:
                try:
                    page_text = await page.evaluate('() => document.body.innerText')
                    
                    # Look for patterns like "1,000 USDC" followed by "1st" or vice versa
                    prize_patterns = [
                        r'(\d{1,3}(?:,\d{3})*)\s*USDC.*?(1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th)',
                        r'(1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th).*?(\d{1,3}(?:,\d{3})*)\s*USDC'
                    ]
                    
                    for pattern in prize_patterns:
                        matches = re.findall(pattern, page_text, re.IGNORECASE | re.DOTALL)
                        
                        for match in matches:
                            if len(match) == 2:
                                # Determine which is amount and which is position
                                if match[0].replace(',', '').isdigit():
                                    amount = int(match[0].replace(',', ''))
                                    position = match[1]
                                else:
                                    amount = int(match[1].replace(',', ''))
                                    position = match[0]
                                
                                prize_breakdown.append({
                                    'position': position,
                                    'amount': amount
                                })
                                print(f"  Strategy 3 - Found prize: {position} = {amount}")
                        
                except Exception as e:
                    print(f"  Strategy 3 failed: {e}")
                    pass
            
            # Extract token type
            token_type = 'USDC'  # default
            try:
                token_element = await page.query_selector('span:has-text("USDC"), span:has-text("SOL"), span:has-text("JUP")')
                if token_element:
                    token_text = await token_element.inner_text()
                    if any(token in token_text.upper() for token in ['USDC', 'SOL', 'JUP']):
                        for token in ['USDC', 'SOL', 'JUP']:
                            if token in token_text.upper():
                                token_type = token
                                break
            except Exception:
                pass
            
            # Expand range positions into individual positions
            expanded_prizes = self.expand_range_positions(prize_breakdown)
            
            # Remove duplicates and sort by position
            unique_prizes = []
            seen_positions = set()
            
            for prize in expanded_prizes:
                pos_key = f"{prize['position']}_{prize['amount']}"
                if pos_key not in seen_positions:
                    unique_prizes.append(prize)
                    seen_positions.add(pos_key)
            
            print(f"  Final extracted prizes: {len(unique_prizes)} prizes")
            for prize in unique_prizes:
                print(f"    {prize['position']}: {prize['amount']}")
            
            return {
                'individual_prizes': unique_prizes,
                'token_type': token_type,
                'total_prizes': len(unique_prizes)
            }
            
        except Exception as e:
            print(f"  ⚠️  Error extracting prize breakdown: {e}")
            return {
                'individual_prizes': [],
                'token_type': 'USDC',
                'total_prizes': 0
            }

    async def extract_total_reward(self, page):
        """Extract total reward amount from the page"""
        try:
            # Look for "Total Prizes" text and associated amount
            total_prize_elements = await page.query_selector_all('p:has-text("Total Prizes")')
            
            for element in total_prize_elements:
                try:
                    # Look for amount in the same container
                    parent = await element.evaluate_handle('element => element.closest("div") || element.closest("td")')
                    amount_elements = await parent.query_selector_all('span, p')
                    
                    for amt_elem in amount_elements:
                        text = await amt_elem.inner_text()
                        # Look for numeric values
                        amount_match = re.search(r'(\d{1,3}(?:,\d{3})*)', text)
                        if amount_match:
                            return int(amount_match.group(1).replace(',', ''))
                except Exception:
                    continue
            
            # Fallback: search page text for total amounts
            page_text = await page.evaluate('() => document.body.innerText')
            
            # Look for patterns like "2000 USDC Total Prizes" or "Total Prizes 2000"
            total_patterns = [
                r'(\d{1,3}(?:,\d{3})*)\s*(?:USDC|SOL|JUP)\s*Total Prizes',
                r'Total Prizes[\s\S]*?(\d{1,3}(?:,\d{3})*)\s*(?:USDC|SOL|JUP)',
                r'(\d{1,3}(?:,\d{3})*)\s*(?:USDC|SOL|JUP)'
            ]
            
            for pattern in total_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Return the largest amount found (likely the total)
                    amounts = [int(match.replace(',', '')) for match in matches]
                    return max(amounts)
            
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error extracting total reward: {e}")
            return None
    
    def extract_slug_from_url(self, url):
        """Extract slug from full URL"""
        if '/listing/' in url:
            return url.split('/listing/')[-1]
        return url

    async def extract_prizes_for_bounty(self, page, url):
        """Extract complete prize information for a single bounty"""
        try:
            print(f"\n🎯 Extracting prizes for: {url}")
            
            # Navigate to the page
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for content to load
            await page.wait_for_timeout(3000)
            
            # Extract title
            title = await page.title() or self.extract_slug_from_url(url).replace('-', ' ').title()
            
            # Extract total reward
            total_reward = await self.extract_total_reward(page)
            
            # Extract prize breakdown
            prize_breakdown = await self.extract_prize_breakdown(page)
            
            # Calculate sum of individual prizes for validation
            individual_sum = sum(prize['amount'] for prize in prize_breakdown['individual_prizes'])
            
            result = {
                'title': title,
                'slug': self.extract_slug_from_url(url),
                'url': url,
                'total_reward': total_reward,
                'prize_breakdown': prize_breakdown,
                'individual_sum': individual_sum,
                'amounts_match': (total_reward == individual_sum) if total_reward else False
            }
            
            print(f"  ✓ Total: {total_reward}, Individual sum: {individual_sum}, Match: {result['amounts_match']}")
            print(f"  ✓ Found {prize_breakdown['total_prizes']} individual prizes")
            
            return result
            
        except Exception as e:
            print(f"  ✗ Error extracting prizes for {url}: {e}")
            return {
                'title': self.extract_slug_from_url(url).replace('-', ' ').title(),
                'slug': self.extract_slug_from_url(url),
                'url': url,
                'total_reward': None,
                'prize_breakdown': {'individual_prizes': [], 'token_type': 'USDC', 'total_prizes': 0},
                'individual_sum': 0,
                'amounts_match': False,
                'error': str(e)
            }

    async def process_bounties_with_prizes(self, bounty_urls):
        """Process multiple bounties and extract prize information"""
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                for url in bounty_urls:
                    result = await self.extract_prizes_for_bounty(page, url)
                    results.append(result)
                    
                    # Small delay between requests
                    await page.wait_for_timeout(2000)
                    
            finally:
                await browser.close()
        
        return results
    
    def merge_prizes_into_descriptions(self, prize_results_file, descriptions_file):
        """Merge extracted prize data into bounty descriptions JSON file"""
        try:
            # Load prize extraction results
            with open(prize_results_file, 'r', encoding='utf-8') as f:
                prize_data = json.load(f)
            
            # Load bounty descriptions
            with open(descriptions_file, 'r', encoding='utf-8') as f:
                descriptions = json.load(f)
            
            # Create a mapping of slug to prize data
            prize_map = {}
            for result in prize_data.get('results', []):
                slug = result.get('slug')
                if slug:
                    prize_map[slug] = {
                        'extracted_prize_data': {
                            'total_reward': result.get('total_reward'),
                            'prize_breakdown': result.get('prize_breakdown', {}),
                            'individual_sum': result.get('individual_sum'),
                            'amounts_match': result.get('amounts_match'),
                            'extraction_successful': result.get('total_reward') is not None
                        }
                    }
            
            # Merge prize data into descriptions
            updated_count = 0
            for bounty in descriptions:
                slug = bounty.get('slug')
                if slug and slug in prize_map:
                    bounty.update(prize_map[slug])
                    updated_count += 1
                else:
                    # Add empty prize data for bounties without extracted prizes
                    bounty['extracted_prize_data'] = {
                        'total_reward': None,
                        'prize_breakdown': {'individual_prizes': [], 'token_type': 'USDC', 'total_prizes': 0},
                        'individual_sum': 0,
                        'amounts_match': False,
                        'extraction_successful': False
                    }
            
            # Save updated descriptions
            with open(descriptions_file, 'w', encoding='utf-8') as f:
                json.dump(descriptions, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Successfully merged prize data into {descriptions_file}")
            print(f"✓ Updated {updated_count} bounties with extracted prize data")
            print(f"✓ Total bounties in file: {len(descriptions)}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error merging prize data: {e}")
            return False
    
    def update_bounty_descriptions_with_prizes(self):
        """Convenience method to merge latest prize extraction results into bounty descriptions"""
        import os
        
        # Find the most recent prize extraction results file
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prize_files = [f for f in os.listdir(project_root) if f.startswith('prize_extraction_results_') and f.endswith('.json')]
        
        if not prize_files:
            print("✗ No prize extraction results files found")
            return False
        
        # Get the most recent file (highest timestamp)
        latest_prize_file = max(prize_files, key=lambda x: float(x.split('_')[-1].replace('.json', '')))
        prize_results_path = os.path.join(project_root, latest_prize_file)
        descriptions_path = os.path.join(project_root, 'output', 'bounty_descriptions.json')
        
        print(f"Using prize results: {latest_prize_file}")
        print(f"Updating descriptions: {descriptions_path}")
        
        return self.merge_prizes_into_descriptions(prize_results_path, descriptions_path)

# Convenience function to run the merge process
if __name__ == "__main__":
    extractor = PrizeExtractor()
    extractor.update_bounty_descriptions_with_prizes()