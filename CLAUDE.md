# PTR Card Generator

## What this project does
Generates 1080x1080 PNG "Federal Stock Report" card images from U.S. House Periodic Transaction Report (PTR) PDFs. These are polished, branded images using the Graveur Variable font and a designer template.

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

The output file path is printed at the end — read it to show the user.

## If party is missing
The card has a `PARTY:` field. If it shows blank, the member isn't in the party lookup dict in `generate_from_url.py`. You can add them to the `PARTY_LOOKUP` dict (key = last name, value = "Republican" or "Democrat").

## If the PDF fails to parse
Some older PTR PDFs are scanned images rather than text-based. The parser will warn "No text extracted from PDF." In this case, the user will need to manually provide the transaction data.

## Key files
- `generate_card.py` — core card image generator (Graveur font, 2550x2550 canvas, downscaled to 1080x1080)
- `generate_from_url.py` — full pipeline: URL → PDF parse → card generation
- `assets/` — background template, Graveur fonts, logos

## Design specs
- Font: Graveur Variable (bundled in assets/)
- Background: designer's InDesign template (assets/template_background.png)
- Colors: Red (200, 61, 52), Green (79, 138, 79)
- Table: up to 6 rows, sorted by amount descending, overflow note for extras
- The "0" in district numbers is rotated 90° to fix Graveur's old-style figures

## Dependencies
```
pip install pdfplumber Pillow numpy requests
```
