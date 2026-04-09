"""Populate country_code (ISO 3166-1 alpha-2) from existing country text.

One-time script. Safe to re-run — only updates rows where country_code is NULL.

Usage:
    PYTHONPATH=. scrapers/.venv/bin/python scripts/normalize_countries.py
    PYTHONPATH=. scrapers/.venv/bin/python scripts/normalize_countries.py --dry-run
"""

import argparse
import logging
import sys

sys.path.insert(0, ".")

from scrapers.shared.db import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Common country name variants → ISO 3166-1 alpha-2
COUNTRY_MAP: dict[str, str] = {
    # Already ISO codes
    "US": "US", "GB": "GB", "DE": "DE", "FR": "FR", "IT": "IT", "ES": "ES",
    "NL": "NL", "CH": "CH", "AT": "AT", "BE": "BE", "SE": "SE", "NO": "NO",
    "DK": "DK", "FI": "FI", "PT": "PT", "IE": "IE", "PL": "PL", "CZ": "CZ",
    "GR": "GR", "RU": "RU", "TR": "TR", "AU": "AU", "NZ": "NZ", "CA": "CA",
    "MX": "MX", "BR": "BR", "AR": "AR", "CL": "CL", "CO": "CO", "PE": "PE",
    "CN": "CN", "JP": "JP", "KR": "KR", "IN": "IN", "SG": "SG", "HK": "HK",
    "TW": "TW", "TH": "TH", "MY": "MY", "ID": "ID", "PH": "PH", "VN": "VN",
    "AE": "AE", "SA": "SA", "IL": "IL", "EG": "EG", "ZA": "ZA", "NG": "NG",
    "KE": "KE", "MA": "MA", "HR": "HR", "RO": "RO", "HU": "HU", "SK": "SK",
    "SI": "SI", "BG": "BG", "LT": "LT", "LV": "LV", "EE": "EE", "LU": "LU",
    "IS": "IS", "MT": "MT", "CY": "CY", "UA": "UA", "RS": "RS", "BA": "BA",
    "MK": "MK", "AL": "AL", "ME": "ME", "GE": "GE", "AM": "AM", "AZ": "AZ",
    "QA": "QA", "KW": "KW", "BH": "BH", "OM": "OM", "JO": "JO", "LB": "LB",
    "PK": "PK", "BD": "BD", "LK": "LK", "NP": "NP", "MM": "MM", "KH": "KH",
    "LA": "LA", "MN": "MN", "KZ": "KZ", "UZ": "UZ",
    "EC": "EC", "UY": "UY", "PY": "PY", "BO": "BO", "VE": "VE", "CR": "CR",
    "PA": "PA", "GT": "GT", "DO": "DO", "CU": "CU", "PR": "PR", "JM": "JM",
    "TT": "TT", "TZ": "TZ", "GH": "GH", "SN": "SN", "CI": "CI", "CM": "CM",
    "ET": "ET", "UG": "UG", "RW": "RW", "MZ": "MZ", "AO": "AO", "TN": "TN",
    "DZ": "DZ", "LY": "LY",
    # Full names
    "UNITED STATES": "US", "UNITED STATES OF AMERICA": "US", "USA": "US",
    "UNITED KINGDOM": "GB", "UK": "GB", "ENGLAND": "GB", "SCOTLAND": "GB", "WALES": "GB",
    "GERMANY": "DE", "FRANCE": "FR", "ITALY": "IT", "SPAIN": "ES",
    "NETHERLANDS": "NL", "THE NETHERLANDS": "NL", "HOLLAND": "NL",
    "SWITZERLAND": "CH", "AUSTRIA": "AT", "BELGIUM": "BE",
    "SWEDEN": "SE", "NORWAY": "NO", "DENMARK": "DK", "FINLAND": "FI",
    "PORTUGAL": "PT", "IRELAND": "IE", "POLAND": "PL",
    "CZECH REPUBLIC": "CZ", "CZECHIA": "CZ",
    "GREECE": "GR", "RUSSIA": "RU", "RUSSIAN FEDERATION": "RU",
    "TURKEY": "TR", "TURKIYE": "TR",
    "AUSTRALIA": "AU", "NEW ZEALAND": "NZ", "CANADA": "CA", "MEXICO": "MX",
    "BRAZIL": "BR", "ARGENTINA": "AR", "CHILE": "CL", "COLOMBIA": "CO", "PERU": "PE",
    "CHINA": "CN", "JAPAN": "JP", "SOUTH KOREA": "KR", "KOREA": "KR",
    "INDIA": "IN", "SINGAPORE": "SG", "HONG KONG": "HK", "TAIWAN": "TW",
    "THAILAND": "TH", "MALAYSIA": "MY", "INDONESIA": "ID",
    "PHILIPPINES": "PH", "VIETNAM": "VN",
    "UNITED ARAB EMIRATES": "AE", "UAE": "AE", "SAUDI ARABIA": "SA",
    "ISRAEL": "IL", "EGYPT": "EG", "SOUTH AFRICA": "ZA",
    "NIGERIA": "NG", "KENYA": "KE", "MOROCCO": "MA",
    "CROATIA": "HR", "ROMANIA": "RO", "HUNGARY": "HU", "SLOVAKIA": "SK",
    "SLOVENIA": "SI", "BULGARIA": "BG", "LITHUANIA": "LT", "LATVIA": "LV",
    "ESTONIA": "EE", "LUXEMBOURG": "LU", "ICELAND": "IS", "MALTA": "MT",
    "CYPRUS": "CY", "UKRAINE": "UA", "SERBIA": "RS",
    "BOSNIA AND HERZEGOVINA": "BA", "BOSNIA": "BA",
    "NORTH MACEDONIA": "MK", "MACEDONIA": "MK",
    "ALBANIA": "AL", "MONTENEGRO": "ME",
    "GEORGIA": "GE", "ARMENIA": "AM", "AZERBAIJAN": "AZ",
    "QATAR": "QA", "KUWAIT": "KW", "BAHRAIN": "BH", "OMAN": "OM",
    "JORDAN": "JO", "LEBANON": "LB",
    "PAKISTAN": "PK", "BANGLADESH": "BD", "SRI LANKA": "LK", "NEPAL": "NP",
    "MYANMAR": "MM", "CAMBODIA": "KH",
    "ECUADOR": "EC", "URUGUAY": "UY", "PARAGUAY": "PY",
    "BOLIVIA": "BO", "VENEZUELA": "VE", "COSTA RICA": "CR", "PANAMA": "PA",
    "GUATEMALA": "GT", "DOMINICAN REPUBLIC": "DO", "CUBA": "CU",
    "PUERTO RICO": "PR", "JAMAICA": "JM", "TRINIDAD AND TOBAGO": "TT",
    "TANZANIA": "TZ", "GHANA": "GH", "SENEGAL": "SN",
    "IVORY COAST": "CI", "COTE D'IVOIRE": "CI",
    "CAMEROON": "CM", "ETHIOPIA": "ET", "UGANDA": "UG", "RWANDA": "RW",
    "MOZAMBIQUE": "MZ", "ANGOLA": "AO", "TUNISIA": "TN",
    "ALGERIA": "DZ", "LIBYA": "LY",
    "KAZAKHSTAN": "KZ", "UZBEKISTAN": "UZ", "MONGOLIA": "MN",
}


def normalize_countries(dry_run: bool):
    client = get_client()

    # Fetch firms with country but no country_code
    offset = 0
    updated = 0
    unmatched: dict[str, int] = {}

    while True:
        result = (
            client.table("firms")
            .select("id, country")
            .not_.is_("country", "null")
            .is_("country_code", "null")
            .range(offset, offset + 999)
            .execute()
        )
        if not result.data:
            break

        for row in result.data:
            country = row["country"].strip()
            code = COUNTRY_MAP.get(country.upper())

            if code:
                if not dry_run:
                    client.table("firms").update(
                        {"country_code": code}
                    ).eq("id", row["id"]).execute()
                updated += 1
            else:
                unmatched[country] = unmatched.get(country, 0) + 1

        if len(result.data) < 1000:
            break
        offset += 1000

    mode = "DRY RUN" if dry_run else "APPLIED"
    logger.info("%s: Updated %d firms with country_code", mode, updated)

    if unmatched:
        logger.warning("Unmatched countries (%d unique):", len(unmatched))
        for name, count in sorted(unmatched.items(), key=lambda x: -x[1]):
            logger.warning("  %s (%d firms)", name, count)


def main():
    parser = argparse.ArgumentParser(description="Normalize country names to ISO codes")
    parser.add_argument("--dry-run", action="store_true", help="Count matches without writing")
    args = parser.parse_args()
    normalize_countries(args.dry_run)


if __name__ == "__main__":
    main()
