import requests
import json
import time

# Heritage = MTG IP core or expansion sets (paper only)
HERITAGE_SETS = [
    # 1993
    "lea", "leb", "2ed", "arn",
    # 1994
    "atq", "3ed", "leg", "drk", "fem",
    # 1995
    "4ed", "ice", "hml",
    # 1996
    "all", "mir",
    # 1997
    "vis", "5ed", "wth", "tmp",
    # 1998
    "sth", "exo", "usg",
    # 1999
    "ulg", "6ed", "uds", "mmq",
    # 2000
    "nem", "pcy", "inv",
    # 2001
    "pls", "7ed", "apc", "ody",
    # 2002
    "tor", "jud", "ons",
    # 2003
    "lgn", "scg", "8ed", "mrd",
    # 2004
    "dst", "5dn", "chk",
    # 2005
    "bok", "sok", "9ed", "rav",
    # 2006
    "gpt", "dis", "csp", "tsp",
    # 2007
    "plc", "fut", "10e", "lrw",
    # 2008
    "mor", "shm", "eve", "ala",
    # 2009
    "con", "arb", "m10", "zen",
    # 2010
    "wwk", "roe", "m11", "som",
    # 2011
    "mbs", "nph", "m12", "isd",
    # 2012
    "dka", "avr", "m13", "rtr",
    # 2013
    "gtc", "dgm", "m14", "ths",
    # 2014
    "bng", "jou", "m15", "ktk",
    # 2015
    "frf", "dtk", "ori", "bfz",
    # 2016
    "ogw", "soi", "emn", "kld",
    # 2017
    "aer", "akh", "hou", "xln",
    # 2018
    "rix", "dom", "m19", "grn",
    # 2019
    "rna", "war", "m20", "eld",
    # 2020
    "thb", "iko", "m21", "znr",
    # 2021
    "khm", "stx", "mid", "vow",
    # 2022
    "neo", "snc", "dmu", "bro",
    # 2023
    "one", "mom", "woe", "lci",
    # 2024
    "mkm", "otj", "blb", "dsk", "fdn",
    # 2025
    "dft", "tdm", "eoe",
    # 2026
    "ecl"
]

print("Step 1: Downloading bulk card data...")
bulk = requests.get("https://api.scryfall.com/bulk-data").json()
default_uri = next(b["download_uri"] for b in bulk["data"] if b["type"] == "default_cards")
all_cards = requests.get(default_uri).json()
print(f"Downloaded {len(all_cards)} total cards")

print("\nStep 2: Filtering to Heritage sets and paper-legal cards...")
heritage_cards = [
    c for c in all_cards 
    if c["set"] in HERITAGE_SETS 
    and c.get("games", []) and "paper" in c.get("games", [])
]
print(f"Found {len(heritage_cards)} Heritage-legal paper cards")

print("\nStep 3: Querying Scryfall for default cards in Heritage sets...")
# Get default cards specifically from Heritage sets
heritage_default_cards_by_name = {}
chunk_size = 30
set_chunks = [HERITAGE_SETS[i:i+chunk_size] for i in range(0, len(HERITAGE_SETS), chunk_size)]

for chunk_idx, set_chunk in enumerate(set_chunks):
    set_filter = " or ".join([f"set:{s}" for s in set_chunk])
    query = f"game:paper is:default ({set_filter})"
    page = 1
    
    print(f"  Chunk {chunk_idx + 1}/{len(set_chunks)}: {', '.join(set_chunk[:3])}...")
    
    while True:
        time.sleep(0.1)
        
        resp = requests.get(
            "https://api.scryfall.com/cards/search",
            params={"q": query, "page": page, "unique": "prints"},
            timeout=30
        )
        
        if resp.status_code == 404:
            break
        elif resp.status_code != 200:
            print(f"    Error: {resp.status_code}")
            break
        
        data = resp.json()
        for card in data.get("data", []):
            name = card["name"]
            # Keep most recent Heritage default for each card name
            if name not in heritage_default_cards_by_name:
                heritage_default_cards_by_name[name] = card
            else:
                if card.get("released_at", "") > heritage_default_cards_by_name[name].get("released_at", ""):
                    heritage_default_cards_by_name[name] = card
        
        if not data.get("has_more", False):
            break
        
        page += 1
        if page > 20:
            break

print(f"Found {len(heritage_default_cards_by_name)} cards with default versions in Heritage sets")

print("\nStep 4: Querying Scryfall for default cards (any set) as fallback...")
# Get ALL default cards for cards that don't have Heritage defaults
all_default_cards_by_name = {}
page = 1

while True:
    print(f"  Fetching page {page}...")
    time.sleep(0.1)
    
    resp = requests.get(
        "https://api.scryfall.com/cards/search",
        params={"q": "game:paper is:default", "page": page, "unique": "cards"},
        timeout=30
    )
    
    if resp.status_code == 404:
        break
    elif resp.status_code != 200:
        print(f"  Error: {resp.status_code}")
        break
    
    data = resp.json()
    for card in data.get("data", []):
        name = card["name"]
        all_default_cards_by_name[name] = card
    
    print(f"  Processed {len(data.get('data', []))} cards (total defaults: {len(all_default_cards_by_name)})")
    
    if not data.get("has_more", False):
        break
    
    page += 1
    if page > 200:
        break

print(f"Found {len(all_default_cards_by_name)} cards with default versions overall")

print("\nStep 5: Building final card database...")
# For each unique card name, pick the best version
best_card_per_name = {}

# First, collect all Heritage printings by name
for card in heritage_cards:
    name = card["name"]
    if name not in best_card_per_name:
        best_card_per_name[name] = []
    best_card_per_name[name].append(card)

# Now pick the best version for each card
final_cards = []
stats = {"default_heritage": 0, "default_any": 0, "most_recent": 0}

for name, printings in best_card_per_name.items():
    chosen_card = None
    
    # Priority 1: Default from Heritage set (most recent if multiple)
    if name in heritage_default_cards_by_name:
        chosen_card = heritage_default_cards_by_name[name]
        chosen_card["is_scryfall_default"] = True
        stats["default_heritage"] += 1
    
    # Priority 2: Default from any set
    elif name in all_default_cards_by_name:
        chosen_card = all_default_cards_by_name[name]
        chosen_card["is_scryfall_default"] = True
        stats["default_any"] += 1
    
    # Priority 3: Most recent Heritage printing
    else:
        chosen_card = max(printings, key=lambda c: c.get("released_at", ""))
        chosen_card["is_scryfall_default"] = False
        stats["most_recent"] += 1
    
    final_cards.append(chosen_card)

print("\nStep 6: Saving to file...")
with open("heritage_cards.json", "w", encoding="utf-8") as f:
    json.dump(final_cards, f, indent=2)

print(f"\n{'='*60}")
print("COMPLETE!")
print(f"{'='*60}")
print(f"Total unique cards: {len(final_cards)}")
print(f"Default from Heritage sets: {stats['default_heritage']}")
print(f"Default from non-Heritage sets: {stats['default_any']}")
print(f"Most recent (no default exists): {stats['most_recent']}")
print(f"\nSaved to heritage_cards.json")
