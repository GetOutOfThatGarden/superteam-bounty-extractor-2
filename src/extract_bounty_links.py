import json
import requests

# Read the JSON file
with open('data/superteam_bounties.json', 'r') as file:
    bounties = json.load(file)

# Extract bounty links
bounty_links = []
for bounty in bounties:
    slug = bounty.get('slug')
    if slug:
        link = f"https://earn.superteam.fun/listing/{slug}"
        bounty_links.append(link)

# Write links to a .txt file
with open('data/bounty_links.txt', 'w') as output_file:
    for link in bounty_links:
        output_file.write(link + '\n')

print(f"Extracted {len(bounty_links)} bounty links to data/bounty_links.txt")


# Add to extract_bounty_links.py
def load_existing_bounties():
    """Load previously processed bounty IDs"""
    try:
        with open('data/processed_bounties.json', 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_processed_bounties(bounty_ids):
    """Save processed bounty IDs"""
    with open('data/processed_bounties.json', 'w') as f:
        json.dump(list(bounty_ids), f)

def save_bounty_data(bounties):
    """Save bounty data to superteam_bounties.json"""
    with open('data/superteam_bounties.json', 'w') as f:
        json.dump(bounties, f, indent=2)
    print(f"Saved {len(bounties)} bounties to data/superteam_bounties.json")

def get_new_bounties_only():
    """Fetch only new bounties from API"""
    existing_ids = load_existing_bounties()
    
    # Fetch all bounties from API
    response = requests.get('https://earn.superteam.fun/api/listings')
    all_bounties = response.json()
    
    # Filter for new bounties only
    new_bounties = [b for b in all_bounties if b['id'] not in existing_ids]
    
    print(f"Found {len(new_bounties)} new bounties out of {len(all_bounties)} total")
    return new_bounties