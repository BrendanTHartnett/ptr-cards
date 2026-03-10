#!/usr/bin/env python3
"""
PTR Card Generator — Generates 1080x1080 Periodic Transaction Report card images.

Usage:
    from generate_card import generate_ptr_card

    data = {
        "filing_id": "20033751",
        "name": "RICHARD W. ALLEN",
        "chamber": "REP.",          # "REP." or "SEN."
        "status": "Member",
        "district": "GA12",         # will be formatted as GA-12
        "party": "REPUBLICAN",      # or "DEMOCRAT"
        "pinned": ["Walmart"],      # optional: asset substrings to pin to top
        "transactions": [
            {
                "asset": "Netflix, Inc. (NFLX)",
                "owner": "SP",      # SP, JT, DC, or ""
                "type": "S",        # P=Purchase, S=Sale
                "tx_date": "12/12/2025",
                "notif_date": "01/06/2026",
                "amount": "$1,001 - $15,000",
                "detail": "",       # optional subtitle line
            },
        ],
    }

    generate_ptr_card(data, "output.png")
"""

from PIL import Image, ImageDraw, ImageFont
import os

# --- Color palette ---
WHITE = (255, 255, 255)
BLACK = (33, 33, 33)
DARK_TEXT = (60, 60, 60)
HEADER_BG = (55, 71, 89)  # dark slate blue table header
HEADER_TEXT = (255, 255, 255)
ROW_ALT = (245, 245, 245)
GREEN = (46, 125, 50)
RED = (183, 28, 28)
BLUE = (0, 0, 180)
BORDER = (180, 180, 180)
SOURCE_GRAY = (130, 130, 130)
DETAIL_GRAY = (150, 150, 150)

# --- Fixed card size ---
CARD_WIDTH = 1080
CARD_HEIGHT = 1080

# --- Layout ---
LEFT_MARGIN = 48
TABLE_LEFT = 48
TABLE_RIGHT = CARD_WIDTH - 48

# Amount range ordering (for sorting by highest first)
AMOUNT_ORDER = {
    "$1,001 - $15,000": 1,
    "$15,001 - $50,000": 2,
    "$50,001 - $100,000": 3,
    "$100,001 - $250,000": 4,
    "$250,001 - $500,000": 5,
    "$500,001 - $1,000,000": 6,
    "$1,000,001 - $5,000,000": 7,
    "$5,000,001 - $25,000,000": 8,
    "$25,000,001 - $50,000,000": 9,
}

AMOUNT_RANGES = {
    "$1,001 - $15,000": (1001, 15000),
    "$15,001 - $50,000": (15001, 50000),
    "$50,001 - $100,000": (50001, 100000),
    "$100,001 - $250,000": (100001, 250000),
    "$250,001 - $500,000": (250001, 500000),
    "$500,001 - $1,000,000": (500001, 1000000),
    "$1,000,001 - $5,000,000": (1000001, 5000000),
    "$5,000,001 - $25,000,000": (5000001, 25000000),
    "$25,000,001 - $50,000,000": (25000001, 50000000),
}


def get_fonts():
    """Load Helvetica fonts."""
    h = "/System/Library/Fonts/Helvetica.ttc"
    fonts = {}
    try:
        fonts["title"] = ImageFont.truetype(h, 40, index=1)
        fonts["info"] = ImageFont.truetype(h, 18)
        fonts["info_bold"] = ImageFont.truetype(h, 18, index=1)
        fonts["summary_count"] = ImageFont.truetype(h, 28, index=1)
        fonts["summary_amt"] = ImageFont.truetype(h, 28, index=1)
        fonts["summary_sep"] = ImageFont.truetype(h, 28)
        fonts["th"] = ImageFont.truetype(h, 13, index=1)
        fonts["td"] = ImageFont.truetype(h, 14)
        fonts["td_bold"] = ImageFont.truetype(h, 14, index=1)
        fonts["td_type"] = ImageFont.truetype(h, 15, index=1)
        fonts["detail"] = ImageFont.truetype(h, 11)
        fonts["source"] = ImageFont.truetype(h, 12)
        fonts["overflow"] = ImageFont.truetype(h, 12, index=1)
    except Exception:
        base = ImageFont.load_default()
        for key in ["title", "info", "info_bold", "summary_count", "summary_amt",
                     "summary_sep", "th", "td", "td_bold", "td_type", "detail",
                     "source", "overflow"]:
            fonts[key] = base
    return fonts


def calc_totals(transactions):
    total_min = sum(AMOUNT_RANGES.get(tx["amount"], (0, 0))[0] for tx in transactions)
    total_max = sum(AMOUNT_RANGES.get(tx["amount"], (0, 0))[1] for tx in transactions)
    return total_min, total_max


def fmt(n):
    return f"${n:,.0f}"


def format_district(district):
    """Convert GA12 -> GA-12, PA08 -> PA-08."""
    letters = ""
    digits = ""
    for c in district:
        if c.isalpha():
            letters += c
        else:
            digits += c
    return f"{letters}-{digits}"


def generate_ptr_card(data, output_path):
    fonts = get_fonts()
    transactions = data["transactions"]
    num_tx = len(transactions)
    total_min, total_max = calc_totals(transactions)

    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    y = 28

    # ── Header: REP./SEN. NAME (STATE-DISTRICT) ──
    prefix = data.get("chamber", "REP.")
    district_fmt = format_district(data["district"])
    header_line = f"{prefix} {data['name']} ({district_fmt})"
    draw.text((LEFT_MARGIN, y), header_line, fill=BLACK, font=fonts["title"])
    y += 48

    # ── Subtitle: Periodic Transaction Report — N Transactions ──
    subtitle = f"Periodic Transaction Report \u2014 {num_tx} Transactions"
    draw.text((LEFT_MARGIN, y), subtitle, fill=SOURCE_GRAY, font=fonts["info"])
    y += 28

    # ── Light grey divider line ──
    draw.line([LEFT_MARGIN, y, CARD_WIDTH - LEFT_MARGIN, y], fill=BORDER, width=1)
    y += 14

    # ── Filing ID ──
    draw.text((LEFT_MARGIN, y), f"Filing ID #{data['filing_id']}", fill=DARK_TEXT, font=fonts["info"])
    y += 24

    # ── Name ──
    draw.text((LEFT_MARGIN, y), "Name: ", fill=DARK_TEXT, font=fonts["info"])
    name_x = LEFT_MARGIN + draw.textlength("Name: ", font=fonts["info"])
    draw.text((name_x, y), data["name"], fill=BLACK, font=fonts["info_bold"])
    y += 24

    # ── Status + State/District + Party ──
    draw.text((LEFT_MARGIN, y), "Status: ", fill=DARK_TEXT, font=fonts["info"])
    sx = LEFT_MARGIN + draw.textlength("Status: ", font=fonts["info"])
    draw.text((sx, y), data["status"], fill=BLACK, font=fonts["info_bold"])

    dist_label_x = LEFT_MARGIN + 230
    draw.text((dist_label_x, y), "State/District: ", fill=DARK_TEXT, font=fonts["info"])
    dx = dist_label_x + draw.textlength("State/District: ", font=fonts["info"])
    draw.text((dx, y), district_fmt, fill=BLACK, font=fonts["info_bold"])

    party_label_x = dx + draw.textlength(district_fmt + "    ", font=fonts["info_bold"])
    draw.text((party_label_x, y), "Party: ", fill=DARK_TEXT, font=fonts["info"])
    px = party_label_x + draw.textlength("Party: ", font=fonts["info"])
    party_color = RED if data["party"] == "REPUBLICAN" else BLUE
    draw.text((px, y), data["party"], fill=party_color, font=fonts["info_bold"])
    y += 36

    # ── Summary line ──
    count_text = f"{num_tx} Transactions"
    sep_text = "  |  "
    amt_text = f"Total Amount: {fmt(total_max)} - {fmt(total_min)}"

    draw.text((LEFT_MARGIN, y), count_text, fill=RED, font=fonts["summary_count"])
    cx = LEFT_MARGIN + draw.textlength(count_text, font=fonts["summary_count"])
    draw.text((cx, y), sep_text, fill=DARK_TEXT, font=fonts["summary_sep"])
    sx2 = cx + draw.textlength(sep_text, font=fonts["summary_sep"])
    draw.text((sx2, y), amt_text, fill=RED, font=fonts["summary_amt"])
    y += 46

    # ── Table ──
    col_asset_x = TABLE_LEFT + 8
    col_owner_x = TABLE_LEFT + 340
    col_type_x = TABLE_LEFT + 400
    col_txdate_x = TABLE_LEFT + 460
    col_notif_x = TABLE_LEFT + 580
    col_amount_x = TABLE_LEFT + 720

    # Table header
    th_h = 34
    draw.rectangle([TABLE_LEFT, y, TABLE_RIGHT, y + th_h], fill=HEADER_BG)
    draw.rectangle([TABLE_LEFT, y, TABLE_RIGHT, y + th_h], outline=HEADER_BG)
    th_y = y + 10
    draw.text((col_asset_x, th_y), "ASSET", fill=HEADER_TEXT, font=fonts["th"])
    draw.text((col_owner_x, th_y), "OWNER", fill=HEADER_TEXT, font=fonts["th"])
    draw.text((col_type_x, th_y), "TYPE", fill=HEADER_TEXT, font=fonts["th"])
    draw.text((col_txdate_x, th_y), "TX DATE", fill=HEADER_TEXT, font=fonts["th"])
    draw.text((col_notif_x, th_y), "NOTIF DATE", fill=HEADER_TEXT, font=fonts["th"])
    draw.text((col_amount_x, th_y), "AMOUNT", fill=HEADER_TEXT, font=fonts["th"])
    y += th_h

    table_top = y

    # Pin specified transactions to top, then sort remainder by amount descending
    pinned_keys = data.get("pinned", [])
    pinned_tx = []
    remaining_tx = []
    if pinned_keys:
        used_indices = set()
        for key in pinned_keys:
            key_lower = key.lower()
            for i, tx in enumerate(transactions):
                if i not in used_indices and key_lower in tx["asset"].lower():
                    pinned_tx.append(tx)
                    used_indices.add(i)
                    break
        remaining_tx = [tx for i, tx in enumerate(transactions) if i not in used_indices]
    else:
        remaining_tx = list(transactions)
    sorted_remaining = sorted(remaining_tx, key=lambda t: AMOUNT_ORDER.get(t["amount"], 0), reverse=True)
    sorted_tx = pinned_tx + sorted_remaining

    # Calculate how many rows fit
    footer_reserve = 80
    available_h = CARD_HEIGHT - y - footer_reserve
    ROW_H_DETAIL = 56
    ROW_H_SIMPLE = 38

    rows_shown = 0
    used_h = 0
    for tx in sorted_tx:
        rh = ROW_H_DETAIL if tx.get("detail") else ROW_H_SIMPLE
        if used_h + rh > available_h:
            break
        used_h += rh
        rows_shown += 1

    overflow_count = num_tx - rows_shown
    display_tx = sorted_tx[:rows_shown]

    # Draw rows
    for i, tx in enumerate(display_tx):
        has_detail = bool(tx.get("detail"))
        rh = ROW_H_DETAIL if has_detail else ROW_H_SIMPLE
        bg = ROW_ALT if i % 2 == 1 else WHITE

        draw.rectangle([TABLE_LEFT, y, TABLE_RIGHT, y + rh], fill=bg)
        draw.line([TABLE_LEFT, y, TABLE_RIGHT, y], fill=BORDER, width=1)

        asset_y = y + 10 if has_detail else y + (rh // 2) - 8
        draw.text((col_asset_x, asset_y), tx["asset"], fill=BLACK, font=fonts["td_bold"])

        if has_detail:
            draw.text((col_asset_x + 4, y + 30), tx["detail"], fill=DETAIL_GRAY, font=fonts["detail"])

        owner = tx.get("owner", "")
        draw.text((col_owner_x, y + (rh // 2) - 8), owner, fill=DARK_TEXT, font=fonts["td"])

        type_char = tx["type"]
        type_color = GREEN if type_char == "P" else RED
        draw.text((col_type_x + 8, y + (rh // 2) - 9), type_char, fill=type_color, font=fonts["td_type"])

        draw.text((col_txdate_x, y + (rh // 2) - 8), tx["tx_date"], fill=DARK_TEXT, font=fonts["td"])
        draw.text((col_notif_x, y + (rh // 2) - 8), tx["notif_date"], fill=DARK_TEXT, font=fonts["td"])
        draw.text((col_amount_x, y + (rh // 2) - 8), tx["amount"], fill=DARK_TEXT, font=fonts["td"])

        y += rh

    # Table borders
    draw.line([TABLE_LEFT, y, TABLE_RIGHT, y], fill=BORDER, width=1)
    draw.line([TABLE_LEFT, table_top - th_h, TABLE_LEFT, y], fill=BORDER, width=1)
    draw.line([TABLE_RIGHT, table_top - th_h, TABLE_RIGHT, y], fill=BORDER, width=1)

    # Footer
    y += 16
    if overflow_count > 0:
        ptr_url = f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/{data['filing_id']}.pdf"
        overflow_text = f"Plus {overflow_count} additional transactions. See {ptr_url} for more."
        draw.text((LEFT_MARGIN, y), overflow_text, fill=DARK_TEXT, font=fonts["overflow"])
        y += 18

    source_y = CARD_HEIGHT - 30
    draw.text((LEFT_MARGIN, source_y),
              "Source: U.S. House of Representatives Financial Disclosure Reports",
              fill=SOURCE_GRAY, font=fonts["source"])

    img.save(output_path, "PNG")
    print(f"Saved: {output_path} ({img.size[0]}x{img.size[1]})")
