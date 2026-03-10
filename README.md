# PTR Card Generator

Generates 1080×1080 PNG card images from congressional Periodic Transaction Reports (PTRs).

## Setup

Requires Python 3 and Pillow:

```bash
pip install Pillow
```

Fonts: uses macOS system Helvetica (`/System/Library/Fonts/Helvetica.ttc`). Falls back to default font on other platforms.

## Usage

```python
from generate_card import generate_ptr_card

data = {
    "filing_id": "20033751",
    "name": "RICHARD W. ALLEN",       # ALL CAPS
    "chamber": "REP.",                 # "REP." or "SEN."
    "status": "Member",
    "district": "GA12",               # no hyphen — formatted on render as GA-12
    "party": "REPUBLICAN",            # "REPUBLICAN" or "DEMOCRAT"
    "pinned": ["Walmart"],            # optional: asset substrings pinned to top
    "transactions": [
        {
            "asset": "Netflix, Inc. (NFLX)",
            "owner": "SP",            # SP, JT, DC, or ""
            "type": "S",              # P=Purchase, S=Sale, E=Exchange
            "tx_date": "12/12/2025",
            "notif_date": "01/06/2026",
            "amount": "$1,001 - $15,000",
            "detail": "",             # optional subtitle
        },
    ],
}

generate_ptr_card(data, "output.png")
```

## Card Design

- **Header**: `REP./SEN. NAME (STATE-DISTRICT)` in bold
- **Summary**: transaction count + total amount range in red
- **Table**: dark slate blue header, color-coded type (P=green, S=red), sorted by amount descending
- **Pinning**: optional list of asset substrings forced to top of table
- **Overflow**: when transactions exceed card height, shows count + link to source PDF

## Data Source

[U.S. House Financial Disclosure Reports](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/)
