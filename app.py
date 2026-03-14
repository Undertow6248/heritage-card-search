"""
Heritage Format Card Search
A Flask web app for searching Magic: The Gathering cards legal in the Heritage format.
Uses Scryfall API for search and prefers default card printings when available.
"""

from flask import Flask, render_template, request, jsonify
import requests
import json
import time
import re

app = Flask(__name__)

# ============================================================================
# LOAD DATA
# ============================================================================

# Load local Heritage card data
with open("heritage_cards.json", encoding="utf-8") as f:
    CARDS = json.load(f)

# Get list of Heritage set codes
HERITAGE_SETS = set(c["set"] for c in CARDS)

# Load ban list (create default from Legacy bans if not found)
try:
    with open("banlist.json", encoding="utf-8") as f:
        BANLIST = set(json.load(f))
except FileNotFoundError:
    BANLIST = set()
    print("No banlist.json found, creating default from Legacy bans...")
    resp = requests.get("https://api.scryfall.com/cards/search", 
                       params={"q": "banned:legacy", "unique": "cards"})
    if resp.status_code == 200:
        legacy_banned = [card["name"] for card in resp.json().get("data", [])]
        with open("banlist.json", "w", encoding="utf-8") as f:
            json.dump(legacy_banned, f, indent=2)
        BANLIST = set(legacy_banned)

# ============================================================================
# PROCESS HERITAGE CARDS
# ============================================================================

# Create a map of card names to their most recent Heritage printing (fallback)
FALLBACK_HERITAGE_CARDS = {}
# Create a map of card names to their default Heritage printing (preferred)
DEFAULT_HERITAGE_CARDS = {}

for card in CARDS:
    name = card["name"]
    
    # Track fallback (most recent)
    if name not in FALLBACK_HERITAGE_CARDS:
        FALLBACK_HERITAGE_CARDS[name] = card
    else:
        if card.get("released_at", "") > FALLBACK_HERITAGE_CARDS[name].get("released_at", ""):
            FALLBACK_HERITAGE_CARDS[name] = card
    
    # Track default printings (using Scryfall's is_scryfall_default flag)
    if card.get("is_scryfall_default"):
        if name not in DEFAULT_HERITAGE_CARDS:
            DEFAULT_HERITAGE_CARDS[name] = card
        else:
            # Keep the most recent default
            if card.get("released_at", "") > DEFAULT_HERITAGE_CARDS[name].get("released_at", ""):
                DEFAULT_HERITAGE_CARDS[name] = card

# Create set of unique card names that are Heritage-legal
HERITAGE_CARD_NAMES = set(FALLBACK_HERITAGE_CARDS.keys())

# Create a set of Heritage-legal card IDs for fast lookup
HERITAGE_CARD_IDS = {c["id"] for c in CARDS}

print(f"Loaded {len(HERITAGE_CARD_NAMES)} unique Heritage cards")
print(f"Found {len(DEFAULT_HERITAGE_CARDS)} cards with default Heritage printings (per Scryfall)")

# Lowercase -> proper-case name map for case-insensitive deck checking
HERITAGE_NAME_LOWER = {n.lower(): n for n in HERITAGE_CARD_NAMES}
for banned in BANLIST:
    if banned.lower() not in HERITAGE_NAME_LOWER:
        HERITAGE_NAME_LOWER[banned.lower()] = banned

# Create set of unique card names that are Heritage-legal
HERITAGE_CARD_NAMES = set(FALLBACK_HERITAGE_CARDS.keys())

# Create a set of Heritage-legal card IDs for fast lookup
HERITAGE_CARD_IDS = {c["id"] for c in CARDS}

# ============================================================================
# SEARCH CACHE
# ============================================================================

CACHE = {}
CACHE_TTL = 3600  # 1 hour

# ============================================================================
# SEARCH FUNCTION
# ============================================================================

def scryfall_search(query):
    """
    Search Scryfall with full syntax support, then filter to Heritage cards.
    
    Process:
    1. Find all Heritage card names matching the query
    2. Use our pre-computed default Heritage printings when available
    3. Fall back to most recent Heritage printing otherwise
    """
    cache_key = f"search:{query}"
    now = time.time()
    
    # Check cache
    if cache_key in CACHE and now - CACHE[cache_key]["time"] < CACHE_TTL:
        return CACHE[cache_key]["data"]
    
    try:
        # Step 1: Find all Heritage card names that match the query
        matching_card_names = set()
        page = 1
        full_query = f"game:paper ({query})"
        
        while True:
            time.sleep(0.1)  # Rate limiting
            resp = requests.get(
                "https://api.scryfall.com/cards/search",
                params={"q": full_query, "page": page, "unique": "cards"},
                timeout=10
            )
            
            if resp.status_code != 200:
                break
            
            data = resp.json()
            for card in data.get("data", []):
                card_name = card["name"]
                if card_name in HERITAGE_CARD_NAMES and card_name not in BANLIST:
                    matching_card_names.add(card_name)
            
            if not data.get("has_more", False):
                break
            
            page += 1
            if page > 20:  # Safety limit
                break
        
        # Step 2: Use our pre-computed default or fallback printings
        results = []
        for card_name in matching_card_names:
            # Prefer default, fall back to most recent
            if card_name in DEFAULT_HERITAGE_CARDS:
                results.append(DEFAULT_HERITAGE_CARDS[card_name])
            else:
                results.append(FALLBACK_HERITAGE_CARDS[card_name])
        
        # Cache results
        CACHE[cache_key] = {"data": results, "time": now}
        return results
        
    except Exception as e:
        print(f"Error searching Scryfall: {e}")
        return []

# ============================================================================
# SORTING FUNCTION
# ============================================================================

def sort_cards(cards, sort_by):
    """Sort cards based on the specified criteria"""
    if sort_by == "name":
        return sorted(cards, key=lambda c: c.get("name", ""))
    
    elif sort_by == "released":
        return sorted(cards, key=lambda c: c.get("released_at", ""), reverse=True)
    
    elif sort_by == "rarity":
        # Order: mythic, rare, uncommon, common, special
        rarity_order = {"mythic": 0, "rare": 1, "uncommon": 2, "common": 3, "special": 4, "bonus": 5}
        return sorted(cards, key=lambda c: rarity_order.get(c.get("rarity", "common"), 99))
    
    elif sort_by == "color":
        # WUBRG order, then colorless, then multicolor
        def color_sort_key(card):
            colors = card.get("colors", [])
            if len(colors) == 0:
                return (99, "")  # Colorless last
            elif len(colors) == 1:
                color_order = {"W": 0, "U": 1, "B": 2, "R": 3, "G": 4}
                return (color_order.get(colors[0], 5), colors[0])
            else:
                return (98, "".join(sorted(colors)))  # Multicolor second to last
        return sorted(cards, key=color_sort_key)
    
    elif sort_by == "power":
        def power_sort_key(card):
            power = card.get("power")
            if power is None:
                return (False, -999)  # Cards without power go to end
            try:
                return (True, float(power))
            except (ValueError, TypeError):
                # Handle */*, X, etc.
                return (True, -1)
        return sorted(cards, key=power_sort_key, reverse=True)
    
    elif sort_by == "toughness":
        def toughness_sort_key(card):
            toughness = card.get("toughness")
            if toughness is None:
                return (False, -999)  # Cards without toughness go to end
            try:
                return (True, float(toughness))
            except (ValueError, TypeError):
                # Handle */*, X, etc.
                return (True, -1)
        return sorted(cards, key=toughness_sort_key, reverse=True)
    
    # Default: no sorting
    return cards

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route("/", methods=["GET"])
def home():
    """Main search page with pagination and sorting"""
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    sort_by = request.args.get("sort", "")
    per_page = 100
    
    # Get cards based on query
    if q:
        all_cards = scryfall_search(q)
        
        # Apply sorting to ALL cards before pagination
        if sort_by:
            all_cards = sort_cards(all_cards, sort_by)
        
        # Pagination
        total_cards = len(all_cards)
        total_pages = (total_cards + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        cards = all_cards[start_idx:end_idx]
    else:
        # No search yet - show empty state
        cards = []
        total_cards = 0
        total_pages = 0
    
    return render_template("index.html", 
                          cards=cards, 
                          query=q, 
                          page=page,
                          total_pages=total_pages,
                          total_cards=total_cards,
                          sort_by=sort_by)

# ============================================================================
# DECK LEGALITY CHECK ROUTE
# ============================================================================

def parse_decklist(text):
    """
    Parse a pasted decklist into a list of (quantity, card_name) tuples.
    Handles formats like:
      4 Lightning Bolt
      4x Lightning Bolt
      Lightning Bolt
      // Sideboard  (section header - skipped)
      Sideboard:   (section header - skipped)
    """
    entries = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        # Skip blank lines, comments, section headers
        if not line or line.startswith("//") or line.lower().startswith("sideboard") or line.startswith("#"):
            continue
        # Match optional quantity prefix: "4 Foo", "4x Foo", or just "Foo"
        m = re.match(r'^(\d+)[xX]?\s+(.+)$', line)
        if m:
            qty = int(m.group(1))
            name = m.group(2).strip()
        else:
            qty = 1
            name = line
        # Strip trailing comments after " // "
        name = re.split(r'\s+//', name)[0].strip()
        if name:
            entries.append((qty, name))
    return entries


@app.route("/check-deck", methods=["POST"])
def check_deck():
    """
    Accept a JSON body with { "decklist": "..." } and return legality results.
    Each entry in the response has:
      - name, quantity, status: "legal" | "banned" | "not_in_format" | "unknown"
    """
    data = request.get_json(force=True)
    decklist_text = data.get("decklist", "")
    entries = parse_decklist(decklist_text)

    results = []
    total = 0
    issues = 0

    for qty, name in entries:
        total += qty
        # Case-insensitive name lookup
        # Build a lowercase lookup map once (cached on first use)
        matched_name = HERITAGE_NAME_LOWER.get(name.lower())

        if matched_name is None:
            status = "unknown"
            issues += qty
        elif matched_name in BANLIST:
            status = "banned"
            issues += qty
        else:
            status = "legal"

        results.append({
            "name": name,
            "matched_name": matched_name,
            "quantity": qty,
            "status": status,
        })

    # Sort: issues first, then legal alphabetically
    order = {"banned": 0, "not_in_format": 1, "unknown": 2, "legal": 3}
    results.sort(key=lambda r: (order.get(r["status"], 9), r["name"].lower()))

    return jsonify({
        "results": results,
        "total_cards": total,
        "issue_count": issues,
        "entry_count": len(results),
    })


# ============================================================================
# RUN APP
# ============================================================================

if __name__ == "__main__":
    app.run(debug=True)

# ============================================================================
# END OF FILE
# ============================================================================
