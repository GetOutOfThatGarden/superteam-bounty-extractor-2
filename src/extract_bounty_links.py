import json

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