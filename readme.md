# Heritage Card Search

A searchable database for Magic: The Gathering's Heritage format, using the Scryfall API.

## What You Need

- A computer running Windows, Mac, or Linux
- Internet connection
- About 10-15 minutes for initial setup

## Installation Instructions

### Step 1: Install Python

**Windows:**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.11 or newer
3. Run the installer
4. **IMPORTANT:** Check the box that says "Add Python to PATH" before clicking Install

**Mac:**
1. Open Terminal (search for "Terminal" in Spotlight)
2. Install Homebrew if you don't have it: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
3. Run: `brew install python`

**Linux:**
- Most Linux systems have Python pre-installed
- If not, run: `sudo apt-get install python3 python3-pip` (Ubuntu/Debian) or equivalent for your distribution

### Step 2: Download the Heritage Card Search Files

1. Download all the files to a folder on your computer (e.g., `mtg-heritage`)
2. You should have these files:
   - `app.py`
   - `fetch_heritage_cards.py`
   - `banlist.json` (will be created automatically if missing)
   - `templates/` folder containing `index.html`

### Step 3: Install Required Packages

**Windows:**
1. Open Command Prompt (search for "cmd" in Start menu)
2. Navigate to your folder: `cd C:\path\to\mtg-heritage`
3. Run: `pip install flask requests`

**Mac/Linux:**
1. Open Terminal
2. Navigate to your folder: `cd /path/to/mtg-heritage`
3. Run: `pip3 install flask requests`

### Step 4: Download Card Data (First Time Only)

This downloads all Heritage-legal cards from Scryfall. **This takes 5-10 minutes.**

**Windows:**
```
python fetch_heritage_cards.py
```

**Mac/Linux:**
```
python3 fetch_heritage_cards.py
```

You'll see progress messages as it downloads. When complete, you'll have a `heritage_cards.json` file.

### Step 5: Run the Web App

**Windows:**
```
python app.py
```

**Mac/Linux:**
```
python3 app.py
```

You should see output like:
```
Loaded 15234 unique Heritage cards
Found 12567 cards with default Heritage printings (per Scryfall)
 * Running on http://127.0.0.1:5000
```

### Step 6: Open in Your Browser

Open your web browser and go to:
```
http://127.0.0.1:5000
```

Or click the link in the terminal output.

## How to Use

### Searching

Use Scryfall syntax in the search box. Examples:

- `lightning bolt` - Find cards by name
- `t:creature` - All creatures
- `c:red` - All red cards
- `cmc=3` - Cards costing exactly 3 mana
- `o:flying t:creature` - Creatures with flying
- `t:instant c:blue cmc<=2` - Blue instants costing 2 or less
- `pow>=5` - Creatures with power 5 or greater

[Full Scryfall syntax guide](https://scryfall.com/docs/syntax)

### Sorting

Use the dropdown to sort results by:
- Name (alphabetical)
- Release Date (newest first)
- Rarity (mythic → rare → uncommon → common)
- Color (WUBRG order)
- Power (highest first)
- Toughness (highest first)

### Double-Faced Cards

Cards with two faces (like transforming cards) have a "↻ Flip" button to view both sides.

### Clicking Cards

Click any card to open its full Scryfall page in a new tab.

## Updating Card Data

When new sets are released or you want to refresh the card database:

1. Stop the web app (press Ctrl+C in the terminal)
2. Run `fetch_heritage_cards.py` again
3. Restart the app with `app.py`

## Editing the Ban List

The ban list is stored in `banlist.json`. Edit this file to add or remove cards:

```json
[
  "Black Lotus",
  "Ancestral Recall",
  "Time Walk"
]
```

Just add or remove card names from the list, save the file, and restart the app.

## Troubleshooting

**"python is not recognized" (Windows)**
- Python wasn't added to PATH during installation
- Reinstall Python and check "Add Python to PATH"

**"No module named flask"**
- Run `pip install flask requests` again

**"Address already in use"**
- Another program is using port 5000
- Stop the other program or change the port in `app.py` (last line: `app.run(debug=True, port=5001)`)

**Cards not showing up**
- Make sure `heritage_cards.json` exists
- Try re-running `fetch_heritage_cards.py`

**Very slow searches**
- First search for any query takes time (hits Scryfall API)
- Subsequent identical searches are cached and instant
- Large searches (like `t:creature`) take longer

## Technical Details

- **Built with:** Python, Flask, Scryfall API
- **Cache:** Search results cached for 1 hour
- **Rate limiting:** 0.1 second delay between Scryfall requests (well under their limits)
- **Data storage:** All card data stored locally in JSON files

## Credits

- Card data from [Scryfall](https://scryfall.com/)
- Heritage format rules and legality maintained by the Heritage community

## Questions or Issues?

If you encounter problems or have questions, please reach out to the Heritage community or check the Scryfall API documentation at [scryfall.com/docs/api](https://scryfall.com/docs/api)
