# Federal Stock Report — PTR Card Generator

Generate polished 1080x1080 card images from Congressional Periodic Transaction Reports (PTRs).

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/BrendanTHartnett/ptr-cards.git
cd ptr-cards
```

### 2. Install dependencies

```bash
pip install pdfplumber Pillow numpy requests
```

### 3. Generate a card from a PTR URL

```bash
python generate_from_url.py "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20033725.pdf"
```

This downloads the PTR PDF, parses the transactions, and generates a card image. The output file is saved in the current directory.

### 4. Or use with Claude

Open Claude Code in the `ptr-cards` directory and paste a PTR link:

```
Generate a PTR card for https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20033725.pdf
```

Claude will read the CLAUDE.md instructions and handle it automatically.

## Where to find PTR links

Go to the [House Financial Disclosures](https://disclosures-clerk.house.gov/FinancialDisclosure) page, search for a member or browse recent filings, and copy the PDF link for any "PTR" filing type.

## Example Output

The generated card includes:
- **The Federal Stock Report** branded header
- Member name, district, party
- Filing ID, transaction count, total amount range
- Top 6 transactions sorted by amount (with overflow note)
- Purchase (P) in green, Sale (S) in red

## Troubleshooting

**"No text extracted from PDF"** — Some older PTRs are scanned images. The parser only works with text-based PDFs (most recent filings are text-based).

**Party field is blank** — The member isn't in the party lookup. Add their last name to `PARTY_LOOKUP` in `generate_from_url.py`.

**Dependencies error** — Make sure you have Python 3.10+ and ran `pip install pdfplumber Pillow numpy requests`.
