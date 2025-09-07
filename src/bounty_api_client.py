import json
import requests
import os

# Get the project root directory (parent of src)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Only run this if the file exists
try:
    # Read the JSON file
    data_file = os.path.join(project_root, 'data', 'superteam_bounties.json')
    with open(data_file, 'r') as file:
        bounties = json.load(file)

    # Extract bounty links
    bounty_links = []
    for bounty in bounties:
        slug = bounty.get('slug')
        if slug:
            link = f"https://earn.superteam.fun/listing/{slug}"
            bounty_links.append(link)

    # Write links to a .txt file
    links_file = os.path.join(project_root, 'data', 'bounty_links.txt')
    with open(links_file, 'w') as output_file:
        for link in bounty_links:
            output_file.write(link + '\n')

    print(f"Extracted {len(bounty_links)} bounty links to data/bounty_links.txt")
except FileNotFoundError:
    print("No existing superteam_bounties.json found. Will create when new bounties are fetched.")


# Add to extract_bounty_links.py
def load_existing_bounties():
    """Load existing bounty IDs from processed_bounties.json"""
    processed_file = os.path.join(project_root, 'data', 'processed_bounties.json')
    try:
        with open(processed_file, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_processed_bounties(bounty_ids):
    """Save processed bounty IDs to processed_bounties.json"""
    processed_file = os.path.join(project_root, 'data', 'processed_bounties.json')
    with open(processed_file, 'w') as f:
        json.dump(list(bounty_ids), f)

def save_bounty_data(bounties):
    """Save bounty data to superteam_bounties.json"""
    data_file = os.path.join(project_root, 'data', 'superteam_bounties.json')
    with open(data_file, 'w') as f:
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