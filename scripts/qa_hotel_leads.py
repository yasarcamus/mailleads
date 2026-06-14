#!/usr/bin/env python3
"""QA-split a produced hotel lead CSV into clean_usable and review_needed.

This script does NOT delete the original production output. It creates a second QA layer:
- clean_usable: rows that are safer for immediate outreach
- review_needed: rows that are source-valid but have operational risk flags

Main risk flags:
- city_missing
- duplicate_email / duplicate_phone / duplicate_domain_email_phone
- free_email
- domain_mismatch
- suspicious_phone
- weak_email_domain
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
FREE_EMAIL_DOMAINS = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yandex.com", "icloud.com", "live.com"}
WEAK_EMAIL_DOMAINS = {"e-cloud.web.tr", "hotelrunner.com", "wix.com", "wordpress.com"}
SECOND_LEVEL_TR = {"com", "net", "org", "edu", "gov", "bel", "k12", "av", "gen", "web"}
CITY_HINTS = {
    "istanbul": "Istanbul",
    "sultanahmet": "Istanbul",
    "beyazit": "Istanbul",
    "laleli": "Istanbul",
    "fatih": "Istanbul",
    "old city": "Istanbul",
    "oldcity": "Istanbul",
    "antalya": "Antalya",
    "alanya": "Antalya",
    "kemer": "Antalya",
    "belek": "Antalya",
    "side": "Antalya",
    "bodrum": "Bodrum",
    "marmaris": "Marmaris",
    "fethiye": "Fethiye",
    "goreme": "Cappadocia",
    "göreme": "Cappadocia",
    "urgup": "Cappadocia",
    "ürgüp": "Cappadocia",
    "uchisar": "Cappadocia",
    "uçhisar": "Cappadocia",
    "cesme": "Cesme",
    "çeşme": "Cesme",
    "alacati": "Alacati",
    "alaçatı": "Alacati",
    "izmir": "Izmir",
    "afyon": "Afyon",
    "pamukkale": "Pamukkale",
    "bursa": "Bursa",
}


def today_istanbul() -> str:
    return (dt.datetime.utcnow() + dt.timedelta(hours=3)).date().isoformat()


def norm(v: str) -> str:
    return re.sub(r"\s+", " ", (v or "").strip().lower())


def domain_of(value: str) -> str:
    value = (value or "").strip().lower()
    if not value:
        return ""
    if "@" in value and "://" not in value:
        d = value.split("@", 1)[1]
    else:
        if not value.startswith(("http://", "https://")):
            value = "https://" + value
        d = urlparse(value).netloc
    d = d.split("@")[-1].split(":")[0]
    if d.startswith("www."):
        d = d[4:]
    return d.strip(".")


def registered_domain(domain: str) -> str:
    parts = (domain or "").lower().split(".")
    if len(parts) <= 2:
        return domain.lower()
    if len(parts) >= 3 and parts[-1] == "tr" and parts[-2] in SECOND_LEVEL_TR:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    if not digits:
        return ""
    if digits.startswith("90") and len(digits) == 12:
        return "+" + digits
    if digits.startswith("0") and len(digits) == 11:
        return "+9" + digits
    if len(digits) == 10:
        return "+90" + digits
    return "+" + digits


def infer_city(row: dict[str, str]) -> str:
    existing = (row.get("city") or "").strip()
    if existing:
        return existing
    haystack = norm(" ".join([
        row.get("hotel_name", ""),
        row.get("website", ""),
        row.get("email_source_url", ""),
        row.get("validation_notes", ""),
    ]))
    for hint, city in CITY_HINTS.items():
        if hint in haystack:
            return city
    # Istanbul bias for +90212 phone and Sultanahmet-heavy seed; mark inferred separately.
    phone = normalize_phone(row.get("phone", ""))
    if phone.startswith("+90212") or phone.startswith("+90216"):
        return "Istanbul"
    return ""


def suspicious_phone(phone: str) -> bool:
    p = normalize_phone(phone)
    digits = re.sub(r"\D", "", p)
    if not digits.startswith("90"):
        return True
    if len(digits) != 12:
        return True
    # Turkish geographic/mobile area codes normally start with 2,3,4,5 after country code.
    if digits[2] not in {"2", "3", "4", "5", "8"}:
        return True
    # 184... looked like call-center / non-standard for hotel line in the generated CSV.
    if digits.startswith("90184"):
        return True
    return False


def same_registered_domain(website: str, email: str) -> bool:
    wd = registered_domain(domain_of(website))
    ed = registered_domain(domain_of(email))
    return bool(wd and ed and wd == ed)


def add_counts(rows: list[dict[str, str]]) -> tuple[Counter, Counter, Counter, Counter]:
    emails = Counter(norm(r.get("verified_email", "")) for r in rows if r.get("verified_email"))
    phones = Counter(normalize_phone(r.get("phone", "")) for r in rows if r.get("phone"))
    domains = Counter(registered_domain(domain_of(r.get("website", ""))) for r in rows if r.get("website"))
    composite = Counter(
        "|".join([
            registered_domain(domain_of(r.get("website", ""))),
            norm(r.get("verified_email", "")),
            normalize_phone(r.get("phone", "")),
        ])
        for r in rows
    )
    return emails, phones, domains, composite


def qa_row(row: dict[str, str], counts: tuple[Counter, Counter, Counter, Counter]) -> dict[str, str]:
    emails, phones, domains, composite = counts
    flags: list[str] = []
    city = infer_city(row)
    if not (row.get("city") or "").strip():
        flags.append("city_inferred" if city else "city_missing")
    email = norm(row.get("verified_email", ""))
    email_domain = domain_of(email)
    website_domain = registered_domain(domain_of(row.get("website", "")))
    phone = normalize_phone(row.get("phone", ""))
    comp = "|".join([website_domain, email, phone])

    if emails[email] > 1:
        flags.append("duplicate_email")
    if phones[phone] > 1:
        flags.append("duplicate_phone")
    if composite[comp] > 1:
        flags.append("duplicate_domain_email_phone")
    if email_domain in FREE_EMAIL_DOMAINS:
        flags.append("free_email")
    if email_domain in WEAK_EMAIL_DOMAINS:
        flags.append("weak_email_domain")
    if email and not same_registered_domain(row.get("website", ""), email):
        # Do not always kill group-property emails, but flag for review.
        flags.append("domain_mismatch")
    if suspicious_phone(row.get("phone", "")):
        flags.append("suspicious_phone")
    if not row.get("email_source_url"):
        flags.append("missing_email_source")
    if not row.get("phone_source_url"):
        flags.append("missing_phone_source")
    try:
        score = int(float(row.get("confidence_score", "0") or 0))
    except ValueError:
        score = 0
    if score < 100:
        flags.append("confidence_below_100")

    out = dict(row)
    out["city"] = city
    out["normalized_domain"] = website_domain
    out["normalized_phone"] = phone
    out["qa_flags"] = ";".join(flags)
    out["qa_status"] = "review_needed" if flags else "clean_usable"
    return out


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_report(path: Path, input_path: Path, all_rows: list[dict[str, str]], clean: list[dict[str, str]], review: list[dict[str, str]], flag_counts: Counter) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Hotel Lead QA Report — {today_istanbul()}\n\n")
        f.write("## Input\n\n")
        f.write(f"- Source CSV: `{input_path}`\n")
        f.write(f"- Total rows checked: {len(all_rows)}\n")
        f.write(f"- Clean usable rows: {len(clean)}\n")
        f.write(f"- Review-needed rows: {len(review)}\n\n")
        f.write("## Flag counts\n\n")
        if flag_counts:
            for flag, count in flag_counts.most_common():
                f.write(f"- {flag}: {count}\n")
        else:
            f.write("- No QA flags.\n")
        f.write("\n## Decision\n\n")
        f.write("Use `clean_usable` for first outreach. Do not mail `review_needed` until manually checked or fixed.\n\n")
        f.write("## Review examples\n\n")
        f.write("| hotel_name | email | phone | website | qa_flags |\n")
        f.write("|---|---|---|---|---|\n")
        for row in review[:30]:
            f.write(f"| {row.get('hotel_name','').replace('|','/')} | {row.get('verified_email','')} | {row.get('phone','')} | {row.get('website','')} | {row.get('qa_flags','')} |\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=f"leads/hotel-a-tier/{today_istanbul()}/touristnettr_hotels_a_tier_{today_istanbul()}.csv")
    args = parser.parse_args()
    input_path = ROOT / args.input
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    counts = add_counts(rows)
    qa_rows = [qa_row(row, counts) for row in rows]
    clean = [r for r in qa_rows if r["qa_status"] == "clean_usable"]
    review = [r for r in qa_rows if r["qa_status"] == "review_needed"]
    fieldnames = list(rows[0].keys()) + ["normalized_domain", "normalized_phone", "qa_flags", "qa_status"]

    run_date = today_istanbul()
    out_dir = ROOT / "leads" / "hotel-a-tier" / run_date / "qa"
    report_dir = ROOT / "reports" / "hotel-a-tier" / run_date / "qa"
    write_csv(out_dir / f"touristnettr_hotels_a_tier_clean_usable_{run_date}.csv", clean, fieldnames)
    write_csv(out_dir / f"touristnettr_hotels_a_tier_review_needed_{run_date}.csv", review, fieldnames)
    write_csv(out_dir / f"touristnettr_hotels_a_tier_qa_full_{run_date}.csv", qa_rows, fieldnames)

    flag_counts = Counter()
    for row in qa_rows:
        for flag in row.get("qa_flags", "").split(";"):
            if flag:
                flag_counts[flag] += 1
    write_report(report_dir / f"touristnettr_hotels_a_tier_qa_report_{run_date}.md", input_path.relative_to(ROOT), qa_rows, clean, review, flag_counts)

    print(f"QA done: {len(clean)} clean, {len(review)} review-needed, {len(qa_rows)} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
