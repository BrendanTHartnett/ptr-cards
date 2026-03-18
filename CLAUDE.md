# PTR Card Generator

## What this project does
Generates 1080x1080 PNG "Federal Stock Report" card images from U.S. House Periodic Transaction Report (PTR) PDFs. These are polished, branded images using the Graveur Variable font and a designer template.

## First-time setup

```bash
cd ~/ptr-cards  # or wherever you cloned it
pip install -r requirements.txt
```

If you don't have the repo yet:
```bash
git clone https://github.com/BrendanTHartnett/ptr-cards.git ~/ptr-cards
cd ~/ptr-cards
pip install -r requirements.txt
```

## How to generate a PTR card from a URL

When the user gives you a PTR PDF URL (from disclosures-clerk.house.gov), run:

```bash
cd ~/ptr-cards
python generate_from_url.py "<URL>"
```

This will:
1. Download the PDF
2. Parse all transactions (asset, owner, type, dates, amounts)
3. Generate a polished 1080x1080 card image
4. Save it as `PTR_NAME_DISTRICT.png` in the current directory

Example:
```bash
python generate_from_url.py "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20033725.pdf"
```

The output file path is printed at the end — read the image to show the user.

## Finding PTR PDFs

To search for recent filings, POST to the House disclosure search:
```bash
curl -s -X POST "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewMemberSearchResult" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "FilingYear=2026&State=&District=&LastName=&FilingType=P" \
  | grep -oE 'ptr-pdfs/2026/[0-9]+' | sort -u
```
Each ID maps to: `https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/<ID>.pdf`

## Key files
- `generate_card.py` — core card image generator (Graveur font, 2550x2550 canvas, downscaled to 1080x1080)
- `generate_from_url.py` — full pipeline: URL -> PDF parse -> card generation. Contains the PDF parser, CSV-based name/party lookup, and card data adapter.
- `assets/members_of_congress.csv` — canonical member names and party affiliations. Two columns: `Name` (e.g. "Rep. Nancy Pelosi") and `Party` (e.g. "Democrat").
- `assets/template_background.png` — designer's background template
- `assets/Graveur-Regular.otf`, `assets/Graveur-Italic.otf` — bundled fonts

## How the name and party work
- The bold title (e.g. "REP. NANCY PELOSI (CA-11)") pulls the member's name exactly from `assets/members_of_congress.csv`, including the Rep./Sen. prefix.
- Party is also looked up from the CSV. If a member isn't found, party shows "Unknown".
- To add or fix a member, edit `assets/members_of_congress.csv` — just add a row like `Rep. John Smith,Republican`.

## Design specs
- Font: Graveur Variable (bundled in assets/)
- Background: designer's InDesign template
- Colors: Red `(200, 61, 52)`, Green `(79, 138, 79)`
- Canvas: 2550x2550, downscaled to 1080x1080
- Table: up to 6 rows, sorted by amount descending, overflow note for extras
- The "0" in district numbers is rotated 90 degrees to fix Graveur's old-style figures
- Purchase = green, Sale = red

## Making changes
- **Card layout/fonts/colors**: edit `generate_card.py`
- **PDF parsing logic**: edit `parse_ptr_pdf()` in `generate_from_url.py`
- **Name/party data**: edit `assets/members_of_congress.csv`
- After making changes, test by generating a card and reading the output image to verify it looks right.
- If you make improvements, commit and push so the changes are shared.
