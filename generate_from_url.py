#!/usr/bin/env python3
"""
Generate a PTR card image from a House disclosure PDF URL.

Usage:
    python generate_from_url.py <PTR_PDF_URL> [output_path]

Examples:
    python generate_from_url.py https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20033725.pdf
    python generate_from_url.py https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20033725.pdf pelosi.png
"""

import io
import os
import re
import sys
import logging
import requests
import pdfplumber
from datetime import datetime
from generate_card import generate_ptr_card

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ptr-from-url")

# ---------------------------------------------------------------------------
# Party lookup from congress_members.json
# ---------------------------------------------------------------------------
import csv
import json

_ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
MEMBERS_CSV_PATH = os.path.join(_ASSETS_DIR, "assets", "members_of_congress.csv")
CONGRESS_JSON_PATH = os.path.join(_ASSETS_DIR, "assets", "congress_members.json")


def _load_members_csv() -> list[dict]:
    """Load members_of_congress.csv into a list of dicts with name/party/chamber."""
    members = []
    try:
        with open(MEMBERS_CSV_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                full = row.get("Name", "").strip()
                party = row.get("Party", "").strip()
                # Parse "Rep. Nancy Pelosi" or "Sen. John Cornyn"
                chamber = ""
                name = full
                if full.startswith("Rep. "):
                    chamber = "House"
                    name = full[5:]
                elif full.startswith("Sen. "):
                    chamber = "Senate"
                    name = full[5:]
                parts = name.split()
                last = parts[-1] if parts else ""
                first = parts[0] if parts else ""
                members.append({
                    "full_name": name,
                    "first": first,
                    "last": last,
                    "party": party,
                    "chamber": chamber,
                })
    except Exception:
        pass
    return members


def _load_party_from_json() -> dict:
    """Fallback: build last_name -> party from congress_members.json."""
    lookup = {}
    try:
        with open(CONGRESS_JSON_PATH) as f:
            data = json.load(f)
        for m in data.get("members", []):
            last = m.get("last_name", "").strip()
            party = m.get("party", "").strip()
            if last and party:
                lookup[last] = party
    except Exception:
        pass
    return lookup


MEMBERS_CSV = _load_members_csv()
PARTY_JSON_FALLBACK = _load_party_from_json()

KNOWN_OWNER_CODES = {"SP", "JT", "DC", "CS"}


def _find_member_csv(name: str) -> dict | None:
    """Find a member in the CSV by matching last name (+ first name if ambiguous)."""
    clean = re.sub(r"(?i)\bHon\.?\s*\.?\s*", "", name).strip()
    parts = clean.split()
    if not parts:
        return None

    last = parts[-1]
    first = parts[0] if len(parts) > 1 else ""

    # Find all CSV matches by last name (case-insensitive)
    matches = [m for m in MEMBERS_CSV if m["last"].lower() == last.lower()]

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1 and first:
        # Disambiguate by first name
        for m in matches:
            if m["first"].lower() == first.lower():
                return m
        # Partial first name match
        for m in matches:
            if m["first"].lower().startswith(first.lower()[:3]):
                return m
        return matches[0]  # fallback to first match
    return None


def canonical_name(pdf_name: str) -> str:
    """Get the canonical name from the CSV, uppercase. Falls back to cleaned PDF name."""
    member = _find_member_csv(pdf_name)
    if member:
        return member["full_name"].upper()
    # Fallback: clean up the PDF name
    clean = re.sub(r"(?i)\bHon\.?\s*\.?\s*", "", pdf_name).strip()
    return clean.upper()


def party_lookup(name: str) -> str:
    """Look up party — CSV first, then JSON fallback."""
    member = _find_member_csv(name)
    if member and member["party"]:
        return member["party"]
    # Fallback to JSON
    clean = re.sub(r"(?i)\bHon\.?\s*\.?\s*", "", name).strip()
    parts = clean.split()
    if parts:
        last = parts[-1]
        for k, v in PARTY_JSON_FALLBACK.items():
            if k.lower() == last.lower():
                return v
    return ""


# ---------------------------------------------------------------------------
# PDF Parser
# ---------------------------------------------------------------------------
def parse_ptr_pdf(pdf_url: str) -> dict:
    """Download and parse a House PTR PDF to extract transaction details."""
    result = {
        "filing_id": "", "member_name": "", "status": "", "state_district": "",
        "transaction_count": 0, "total_low": 0, "total_high": 0,
        "transactions": [], "parse_success": False,
    }

    log.info("Downloading PDF: %s", pdf_url)
    try:
        resp = requests.get(pdf_url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        log.error("Failed to download PDF: %s", e)
        return result

    try:
        full_text = ""
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        if not full_text:
            log.warning("No text extracted from PDF.")
            return result

        # Extract header info
        fid = re.search(r'Filing ID\s*#?(\d+)', full_text)
        if fid:
            result["filing_id"] = fid.group(1)

        name = re.search(r'Name:\s*(.+?)(?:\n|$)', full_text)
        if name:
            result["member_name"] = name.group(1).strip()

        status = re.search(r'Status:\s*(.+?)(?:\n|$)', full_text)
        if status:
            result["status"] = status.group(1).strip()

        sd = re.search(r'State/District:\s*(.+?)(?:\n|$)', full_text)
        if sd:
            result["state_district"] = sd.group(1).strip()

        # Join split amounts across lines
        full_text = re.sub(
            r'\$([\d,]+)\s*-\s*\n([^\n]{0,80}?)\$([\d,]+)',
            r'$\1 - $\3', full_text
        )

        # Build a map of continuation lines (lines with [XX] type codes but no dates)
        # These are wrapped asset names that follow a transaction line
        lines = full_text.split('\n')
        continuation_map = {}  # line_number -> continuation text
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if (re.search(r'\[[A-Z]{2,4}\]', stripped)
                    and not re.search(r'\d{1,2}/\d{1,2}/\d{4}', stripped)
                    and not stripped.startswith('*')
                    and idx > 0):
                continuation_map[idx] = stripped

        # Regex for transactions
        txn_pattern = re.compile(
            r'([^\n]*?)\s+'
            r'(P|S|S \(partial\)|E)\s+'
            r'(\d{1,2}/\d{1,2}/\d{4})\s+'
            r'(\d{1,2}/\d{1,2}/\d{4})\s+'
            r'\$([\d,]+)\s*-\s*\$([\d,]+)',
        )

        raw_matches = txn_pattern.findall(full_text)

        # Post-process: find continuation lines and append to asset names
        # First find which line each match is on
        matches = []
        for m in raw_matches:
            asset_raw = m[0]
            # Find which line this match is on
            match_line_idx = None
            for idx, line in enumerate(lines):
                if asset_raw.strip() in line and re.search(r'\d{1,2}/\d{1,2}/\d{4}', line):
                    match_line_idx = idx
                    break
            # Check if the next line is a continuation
            continuation = ""
            if match_line_idx is not None and (match_line_idx + 1) in continuation_map:
                continuation = " " + continuation_map[match_line_idx + 1]
            # Rebuild the match tuple with appended continuation
            matches.append((m[0] + continuation, *m[1:]))

        if not matches:
            # Fallback
            amount_pattern = re.compile(r'\$([\d,]+)\s*-\s*\$([\d,]+)')
            all_amounts = amount_pattern.findall(full_text)
            if all_amounts:
                for low_str, high_str in all_amounts:
                    low = int(low_str.replace(",", ""))
                    high = int(high_str.replace(",", ""))
                    result["transactions"].append({
                        "owner": "", "asset": "Unknown", "type": "?",
                        "txn_date": "", "notif_date": "",
                        "amount_low": low, "amount_high": high,
                        "amount_display": f"${low:,} - ${high:,}",
                    })
                result["transaction_count"] = len(result["transactions"])
                result["total_low"] = sum(t["amount_low"] for t in result["transactions"])
                result["total_high"] = sum(t["amount_high"] for t in result["transactions"])
                result["parse_success"] = True
                return result
            log.warning("No transaction patterns found in PDF.")
            return result

        for match in matches:
            asset_raw, txn_type, txn_date, notif_date, low_str, high_str = match
            low = int(low_str.replace(",", ""))
            high = int(high_str.replace(",", ""))

            asset_text = asset_raw.strip()
            if "Owner" in asset_text and "Asset" in asset_text:
                continue
            if "ID" == asset_text.strip() or not asset_text:
                continue

            owner = ""
            first_word = asset_text.split()[0] if asset_text else ""
            if first_word in KNOWN_OWNER_CODES:
                owner = first_word
                asset_text = asset_text[len(first_word):].strip()

            # Preserve asset type code [ST], [CS], etc. but clean up other artifacts
            asset_clean = re.sub(r'\s+New\s*$', '', asset_text).strip()
            # Extract the type code if present
            code_match = re.search(r'\s*(\[[A-Z]{2,4}\])\s*$', asset_clean)
            asset_type_code = code_match.group(1) if code_match else ""
            if code_match:
                asset_clean = asset_clean[:code_match.start()].strip()
            if len(asset_clean) > 80:
                asset_clean = asset_clean[:77] + "..."
            # Reattach the type code
            if asset_type_code:
                asset_clean = f"{asset_clean} {asset_type_code}"

            # Check if partial
            is_partial = "partial" in txn_type.lower()

            result["transactions"].append({
                "owner": owner, "asset": asset_clean, "type": txn_type[0],
                "partial": is_partial,
                "txn_date": txn_date, "notif_date": notif_date,
                "amount_low": low, "amount_high": high,
                "amount_display": f"${low:,} - ${high:,}",
            })

        result["transaction_count"] = len(result["transactions"])
        result["total_low"] = sum(t["amount_low"] for t in result["transactions"])
        result["total_high"] = sum(t["amount_high"] for t in result["transactions"])
        result["parse_success"] = True
        log.info("Parsed %d transactions from PDF.", len(result["transactions"]))

    except Exception as e:
        log.error("Failed to parse PDF: %s", e)

    return result


# ---------------------------------------------------------------------------
# Convert parsed PDF data to card format
# ---------------------------------------------------------------------------
def pdf_to_card_data(pdf_url: str, pdf_data: dict) -> dict:
    """Convert parsed PDF data into the format generate_ptr_card expects."""
    # Extract doc_id from URL
    doc_id_match = re.search(r'/(\d+)\.pdf', pdf_url)
    doc_id = doc_id_match.group(1) if doc_id_match else ""

    # Get canonical name from CSV (uppercase)
    raw_name = pdf_data.get("member_name", "")
    name = canonical_name(raw_name)

    # District from PDF
    district_raw = pdf_data.get("state_district", "")
    district = district_raw.strip()

    return {
        "filing_id": pdf_data.get("filing_id") or doc_id,
        "name": name,
        "chamber": "REP.",
        "status": pdf_data.get("status", "Member"),
        "district": district,
        "party": party_lookup(raw_name),
        "pinned": [],
        "transactions": [
            {
                "asset": t["asset"],
                "owner": t["owner"],
                "type": t["type"],
                "partial": t.get("partial", False),
                "tx_date": t["txn_date"],
                "notif_date": t["notif_date"],
                "amount": t["amount_display"],
                "detail": "",
            }
            for t in pdf_data.get("transactions", [])
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def generate_from_url(pdf_url: str, output_path: str = None) -> str:
    """Full pipeline: URL -> parse PDF -> generate card. Returns output path."""
    # Parse
    pdf_data = parse_ptr_pdf(pdf_url)
    if not pdf_data["parse_success"]:
        log.error("Failed to parse PTR PDF. Cannot generate card.")
        return None

    # Convert
    card_data = pdf_to_card_data(pdf_url, pdf_data)

    # Default output filename
    if not output_path:
        safe_name = card_data["name"].replace(" ", "_").replace(".", "")
        district = card_data["district"]
        output_path = f"PTR_{safe_name}_{district}.png"

    # Generate
    generate_ptr_card(card_data, output_path)
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_from_url.py <PTR_PDF_URL> [output_path]")
        print("\nExample:")
        print("  python generate_from_url.py https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20033725.pdf")
        sys.exit(1)

    url = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    result = generate_from_url(url, out)
    if result:
        print(f"\nCard saved to: {result}")
