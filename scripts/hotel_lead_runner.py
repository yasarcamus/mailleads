#!/usr/bin/env python3
"""
TouristNetTR daily hotel lead crawler.

Production rule after 2026-06-15 change:
- Target is 10 usable hotel leads per daily run, not 145 perfect A-tier leads.
- Decision-maker data is optional.
- Phone/WhatsApp is optional.
- A lead is approved when it is a real hotel/accommodation business, has a source-valid hotel email, and has a plausible TouristNetTR integration point.
- No guessed or pattern-generated emails are allowed.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import hashlib
import html
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED_FILE = ROOT / "seeds" / "hotel_seed_domains.csv"
DEFAULT_QUERY_FILE = ROOT / "seeds" / "city_queries.csv"

CSV_COLUMNS = [
    "run_date",
    "lead_id",
    "hotel_name",
    "city",
    "hotel_type_or_segment",
    "website",
    "instagram",
    "phone",
    "verified_email",
    "email_source_url",
    "website_source_url",
    "instagram_source_url",
    "phone_source_url",
    "decision_maker_name",
    "decision_maker_source_url",
    "confidence_score",
    "action_class",
    "best_first_contact_channel",
    "touristnettr_integration_point",
    "short_note",
    "reason_for_fit",
    "validation_notes",
]

CONTACT_LINK_KEYWORDS = (
    "contact", "iletisim", "iletişim", "reservation", "rezervasyon", "booking",
    "kvkk", "corporate", "kurumsal", "about", "hakkimizda", "hakkımızda",
    "sales", "satis", "satış", "front-office", "frontoffice", "guest", "misafir",
)
HOTEL_INCLUDE_KEYWORDS = (
    "hotel", "otel", "boutique", "butik", "resort", "thermal", "termal",
    "spa", "cave", "city", "suites", "suite", "inn", "konak", "palace", "beach",
    "apart hotel", "aparthotel", "rooms", "accommodation", "lodging", "guest house",
)
STRICT_EXCLUDE_KEYWORDS = (
    "airbnb", "villa", "villas", "emlak", "real estate", "property management",
    "property manager", "rent a car", "rental car", "travel agency", "dmc",
    "restaurant", "restoran", "cafe", "kafe", "exchange", "western union",
    "phone shop", "dorm", "yurt", "camp", "camping", "hostel",
)
NOISE_EMAIL_DOMAINS = {
    "example.com", "domain.com", "sentry.io", "wix.com", "wordpress.com",
    "cloudflare.com", "google.com", "googlemail.com", "schema.org", "w3.org",
    "facebook.com", "instagram.com", "booking.com", "tripadvisor.com", "expedia.com",
}
COMMON_FREE_EMAIL_DOMAINS = {
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yandex.com", "icloud.com", "live.com"
}
TRAVEL_BOOKING_DOMAINS = (
    "booking.", "tripadvisor.", "expedia.", "agoda.", "hotels.com", "trivago.",
    "airbnb.", "vrbo.", "etstur.", "tatilsepeti.", "jollytur.",
)

EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+-])([A-Z0-9._%+\-]{1,64}@[A-Z0-9.\-]{2,255}\.[A-Z]{2,24})(?![A-Z0-9._%+-])")
PHONE_RE = re.compile(r"(?x)((?:\+?90|0)?\s*(?:\(?\d{3}\)?[\s.\-]*)\d{3}[\s.\-]*\d{2}[\s.\-]*\d{2})")
CFEMAIL_RE = re.compile(r'data-cfemail=["\']([0-9a-fA-F]+)["\']')
CFEMAIL_HASH_RE = re.compile(r"/cdn-cgi/l/email-protection#([0-9a-fA-F]+)")


@dataclasses.dataclass
class Prospect:
    hotel_name: str
    city: str
    website: str
    segment: str = ""
    instagram: str = ""
    source: str = "seed"


@dataclasses.dataclass
class ExtractedContact:
    email: str = ""
    email_source_url: str = ""
    email_note: str = ""
    phone: str = ""
    phone_source_url: str = ""
    instagram: str = ""
    instagram_source_url: str = ""
    pages_checked: int = 0
    checked_urls: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Lead:
    run_date: str
    lead_id: str
    hotel_name: str
    city: str
    hotel_type_or_segment: str
    website: str
    instagram: str
    phone: str
    verified_email: str
    email_source_url: str
    website_source_url: str
    instagram_source_url: str
    phone_source_url: str
    decision_maker_name: str
    decision_maker_source_url: str
    confidence_score: int
    action_class: str
    best_first_contact_channel: str
    touristnettr_integration_point: str
    short_note: str
    reason_for_fit: str
    validation_notes: str

    def to_row(self) -> dict[str, str | int]:
        return dataclasses.asdict(self)


class SuppressionIndex:
    def __init__(self) -> None:
        self.hotel_names: set[str] = set()
        self.domains: set[str] = set()
        self.phones: set[str] = set()
        self.instagrams: set[str] = set()
        self.emails: set[str] = set()
        self.lead_ids: set[str] = set()

    def add_row(self, row: dict[str, str]) -> None:
        self.lead_ids.add(norm(row.get("lead_id", "")))
        self.hotel_names.add(norm(row.get("hotel_name", "")))
        domain = domain_of(row.get("website", ""))
        if domain:
            self.domains.add(domain)
        phone = normalize_phone(row.get("phone", ""))
        if phone:
            self.phones.add(phone)
        insta = normalize_instagram(row.get("instagram", ""))
        if insta:
            self.instagrams.add(insta)
        email = norm_email(row.get("verified_email", ""))
        if email:
            self.emails.add(email)

    def is_duplicate(self, prospect: Prospect, contact: ExtractedContact, lead_id: str) -> bool:
        return any([
            norm(lead_id) in self.lead_ids,
            norm(prospect.hotel_name) in self.hotel_names,
            domain_of(prospect.website) in self.domains if domain_of(prospect.website) else False,
            normalize_phone(contact.phone) in self.phones if contact.phone else False,
            normalize_instagram(contact.instagram or prospect.instagram) in self.instagrams if (contact.instagram or prospect.instagram) else False,
            norm_email(contact.email) in self.emails if contact.email else False,
        ])


def now_istanbul_date() -> str:
    return (dt.datetime.utcnow() + dt.timedelta(hours=3)).date().isoformat()


def norm(value: str) -> str:
    value = (value or "").strip().lower()
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value


def norm_email(value: str) -> str:
    return norm(value).strip(".,;:()[]{}<>")


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    if not digits:
        return ""
    if digits.startswith("90") and len(digits) == 12:
        return "+" + digits
    if digits.startswith("0") and len(digits) == 11:
        return "+9" + digits
    if len(digits) == 10:
        return "+90" + digits
    return "+" + digits if (value or "").strip().startswith("+") else digits


def normalize_instagram(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else "https://" + value)
    if "instagram.com" not in parsed.netloc.lower():
        return norm(value)
    path = parsed.path.strip("/").split("/")[0]
    return "@" + path.lower() if path else ""


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def domain_of(url_or_email: str) -> str:
    value = (url_or_email or "").strip().lower()
    if not value:
        return ""
    if "@" in value and "://" not in value:
        value = value.split("@", 1)[1]
    else:
        value = normalize_url(value)
        value = urlparse(value).netloc
    value = value.split("@")[-1].split(":")[0]
    if value.startswith("www."):
        value = value[4:]
    return value.strip(".")


def registered_domain(domain: str) -> str:
    parts = (domain or "").lower().split(".")
    if len(parts) <= 2:
        return domain.lower()
    second_level_cc = {"com", "net", "org", "edu", "gov", "bel", "k12", "av", "gen", "web"}
    if len(parts) >= 3 and parts[-1] == "tr" and parts[-2] in second_level_cc:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def same_registered_domain(a: str, b: str) -> bool:
    da = registered_domain(domain_of(a))
    db = registered_domain(domain_of(b))
    return bool(da and db and da == db)


def decode_cfemail(encoded: str) -> str:
    try:
        data = bytes.fromhex(encoded)
        key = data[0]
        return "".join(chr(b ^ key) for b in data[1:])
    except Exception:
        return ""


def clean_email(email: str) -> str:
    return norm_email(email).replace("mailto:", "").strip("<>\"'")


def is_noise_email(email: str) -> bool:
    email = clean_email(email)
    domain = domain_of(email)
    if not email or "@" not in email:
        return True
    if domain in NOISE_EMAIL_DOMAINS:
        return True
    local = email.split("@", 1)[0]
    if local in {"example", "test", "yourname", "name", "email", "mail"}:
        return True
    if any(email.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
        return True
    return False


def looks_like_hotel_fit(prospect: Prospect, page_text: str = "") -> tuple[bool, str]:
    haystack = norm(" ".join([prospect.hotel_name, prospect.segment, prospect.website, page_text[:5000]]))
    has_hotel_signal = any(k in haystack for k in HOTEL_INCLUDE_KEYWORDS)
    has_strict_exclusion = any(k in haystack for k in STRICT_EXCLUDE_KEYWORDS)
    if has_strict_exclusion and not has_hotel_signal:
        return False, "Excluded by non-hotel keywords."
    if has_hotel_signal:
        return True, "Hotel/accommodation keywords verified."
    return False, "Hotel fit not clear enough."


def infer_integration_point(text: str) -> str:
    hay = norm(text[:5000])
    if "reservation" in hay or "rezervasyon" in hay or "booking" in hay:
        return "reservation confirmation / pre-arrival email"
    if "whatsapp" in hay or "check-in" in hay or "check in" in hay:
        return "WhatsApp check-in / pre-arrival message"
    if "reception" in hay or "front office" in hay or "frontoffice" in hay:
        return "reception QR / front-office guest handoff"
    if "room" in hay or "oda" in hay or "guest" in hay or "misafir" in hay:
        return "guest welcome message / room QR"
    return "reservation email / reception QR"


def request_get(session: requests.Session, url: str, timeout: int = 15) -> Optional[requests.Response]:
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400:
            return None
        content_type = resp.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "application/xhtml" not in content_type and content_type:
            return None
        return resp
    except requests.RequestException:
        return None


def soup_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def extract_instagram(soup: BeautifulSoup) -> str:
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "instagram.com" in href.lower():
            return normalize_instagram(href)
    return ""


def extract_emails_from_html(raw_html: str, soup: BeautifulSoup) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = html.unescape(a["href"])
        if href.lower().startswith("mailto:"):
            email = clean_email(href.split(":", 1)[1].split("?", 1)[0])
            if not is_noise_email(email):
                found.append((email, "mailto"))
    for match in EMAIL_RE.finditer(html.unescape(raw_html)):
        email = clean_email(match.group(1))
        if not is_noise_email(email):
            found.append((email, "html"))
    for encoded in CFEMAIL_RE.findall(raw_html) + CFEMAIL_HASH_RE.findall(raw_html):
        email = clean_email(decode_cfemail(encoded))
        if email and not is_noise_email(email):
            found.append((email, "cloudflare"))
    deduped, seen = [], set()
    for email, kind in found:
        if email not in seen:
            seen.add(email)
            deduped.append((email, kind))
    return deduped


def extract_phones_from_text(text: str) -> list[str]:
    phones, seen = [], set()
    for match in PHONE_RE.finditer(text):
        phone = normalize_phone(match.group(1))
        if phone and phone not in seen and len(re.sub(r"\D", "", phone)) >= 10:
            seen.add(phone)
            phones.append(phone)
    return phones


def candidate_contact_links(base_url: str, soup: BeautifulSoup, max_links: int) -> list[str]:
    base_domain = registered_domain(domain_of(base_url))
    links, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "tel:", "mailto:")):
            continue
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if registered_domain(domain_of(url)) != base_domain:
            continue
        hay = norm(url + " " + a.get_text(" ", strip=True))
        if any(k in hay for k in CONTACT_LINK_KEYWORDS):
            canonical = parsed._replace(fragment="", query="").geturl()
            if canonical not in seen:
                seen.add(canonical)
                links.append(canonical)
        if len(links) >= max_links:
            break
    return links


def pick_best_email(emails: list[tuple[str, str, str]], official_domain: str) -> tuple[str, str, str]:
    if not emails:
        return "", "", ""
    official_reg = registered_domain(official_domain)

    def email_score(item: tuple[str, str, str]) -> int:
        email, _source_url, kind = item
        local, domain = email.split("@", 1)
        local = local.lower()
        score = 0
        if registered_domain(domain) == official_reg:
            score += 50
        score += {"cloudflare": 30, "mailto": 25, "html": 15}.get(kind, 0)
        score += {
            "sales": 15,
            "reservation": 15,
            "reservations": 15,
            "booking": 12,
            "info": 10,
            "contact": 8,
            "frontoffice": 8,
            "reception": 8,
            "guestrelations": 8,
        }.get(local, 0)
        if domain in COMMON_FREE_EMAIL_DOMAINS:
            score -= 5
        return score

    email, url, kind = max(emails, key=email_score)
    note_map = {
        "cloudflare": "Email decoded from Cloudflare email-protection on official/relevant hotel page.",
        "mailto": "Email extracted from mailto link on official/relevant hotel page.",
        "html": "Email extracted from official/relevant hotel page HTML/text.",
    }
    return email, url, note_map.get(kind, "Email extracted from source page.")


def compute_confidence(prospect: Prospect, contact: ExtractedContact, page_text: str) -> int:
    score = 40
    if prospect.website:
        score += 10
    fit, _ = looks_like_hotel_fit(prospect, page_text)
    if fit:
        score += 20
    if contact.email and contact.email_source_url:
        score += 25
    if contact.phone and contact.phone_source_url:
        score += 5
    if contact.email and same_registered_domain(contact.email, prospect.website):
        score += 10
    elif domain_of(contact.email) in COMMON_FREE_EMAIL_DOMAINS:
        score -= 5
    if contact.email_note.startswith("Email decoded"):
        score += 5
    if contact.pages_checked >= 2:
        score += 5
    return min(100, max(0, score))


def best_first_contact_channel(contact: ExtractedContact) -> str:
    local = contact.email.split("@", 1)[0].lower() if contact.email else ""
    if local in {"sales", "reservation", "reservations", "booking"}:
        return "email"
    if contact.email:
        return "email"
    if contact.phone:
        return "phone"
    return "manual_review"


def build_lead_id(prospect: Prospect, email: str) -> str:
    domain = registered_domain(domain_of(prospect.website)) or domain_of(email)
    base = "__".join([norm(prospect.hotel_name), norm(prospect.city), norm(domain or email)])
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    digest = hashlib.sha1((base + "|" + norm_email(email)).encode("utf-8")).hexdigest()[:10]
    return f"{base}-{digest}"[:120]


def infer_segment(prospect: Prospect, text: str) -> str:
    hay = norm(" ".join([prospect.hotel_name, text[:3000]]))
    if "cave" in hay or "mağara" in hay or "magara" in hay:
        return "cave hotel"
    if "thermal" in hay or "termal" in hay:
        return "thermal hotel"
    if "resort" in hay:
        return "resort hotel"
    if "boutique" in hay or "butik" in hay:
        return "boutique hotel"
    if "beach" in hay or "plaj" in hay:
        return "beach hotel"
    if "apart" in hay or "suite" in hay:
        return "apart/suite hotel"
    if "spa" in hay:
        return "spa hotel"
    return "hotel"


def inspect_prospect(session: requests.Session, prospect: Prospect, max_pages: int, sleep_seconds: float, min_confidence: int) -> tuple[Optional[Lead], dict[str, str]]:
    website = normalize_url(prospect.website)
    if not website:
        return None, {"reason": "missing_website"}
    resp = request_get(session, website)
    if resp is None:
        return None, {"reason": "homepage_fetch_failed", "website": website}

    homepage_url = resp.url
    official_domain = domain_of(homepage_url)
    pages_to_check = [homepage_url]
    emails: list[tuple[str, str, str]] = []
    phones: list[tuple[str, str]] = []
    page_texts: list[str] = []
    instagram = normalize_instagram(prospect.instagram)
    instagram_source_url = ""

    soup = BeautifulSoup(resp.text, "lxml")
    page_texts.append(soup_text(soup))
    if not instagram:
        instagram = extract_instagram(soup)
        if instagram:
            instagram_source_url = homepage_url
    for link in candidate_contact_links(homepage_url, soup, max_links=max_pages - 1):
        if link not in pages_to_check:
            pages_to_check.append(link)

    checked_urls: list[str] = []
    for url in pages_to_check[:max_pages]:
        if sleep_seconds:
            time.sleep(sleep_seconds)
        r = resp if url == homepage_url else request_get(session, url)
        if r is None:
            continue
        checked_urls.append(r.url)
        s = BeautifulSoup(r.text, "lxml")
        text = soup_text(s)
        page_texts.append(text)
        if not instagram:
            instagram = extract_instagram(s)
            if instagram:
                instagram_source_url = r.url
        # Email must be found on the official hotel domain. The email itself may be info@, reservations@, or even a free mailbox if it is visibly published by the hotel.
        for email, kind in extract_emails_from_html(r.text, s):
            if registered_domain(domain_of(r.url)) == registered_domain(official_domain):
                emails.append((email, r.url, kind))
        for phone in extract_phones_from_text(text):
            phones.append((phone, r.url))

    combined_text = " ".join(page_texts)
    fit_ok, fit_reason = looks_like_hotel_fit(prospect, combined_text)
    if not fit_ok:
        return None, {"reason": "hotel_fit_failed", "detail": fit_reason, "website": website}

    email, email_url, email_note = pick_best_email(emails, official_domain)
    if not email:
        return None, {"reason": "no_source_valid_hotel_email", "website": website, "pages_checked": str(len(checked_urls))}

    phone, phone_url = (phones[0] if phones else ("", ""))
    contact = ExtractedContact(
        email=email,
        email_source_url=email_url,
        email_note=email_note,
        phone=phone,
        phone_source_url=phone_url,
        instagram=instagram,
        instagram_source_url=instagram_source_url,
        pages_checked=len(checked_urls),
        checked_urls=checked_urls,
    )
    confidence = compute_confidence(prospect, contact, combined_text)
    if confidence < min_confidence:
        return None, {"reason": "confidence_below_minimum", "confidence": str(confidence), "website": website, "email": email}

    run_date = now_istanbul_date()
    lead_id = build_lead_id(prospect, email)
    segment = prospect.segment or infer_segment(prospect, combined_text)
    integration_point = infer_integration_point(combined_text)
    validation_notes = "; ".join(x for x in [
        email_note,
        "Phone optional; not required for daily email-ready lead." if not phone else "Phone found on source page.",
        f"Checked URLs: {', '.join(checked_urls[:5])}" if checked_urls else "",
        "Decision maker optional by 2026-06-15 rule change.",
        "No inferred email used.",
    ] if x)
    lead = Lead(
        run_date=run_date,
        lead_id=lead_id,
        hotel_name=prospect.hotel_name,
        city=prospect.city,
        hotel_type_or_segment=segment,
        website=homepage_url,
        instagram=instagram,
        phone=phone,
        verified_email=email,
        email_source_url=email_url,
        website_source_url=homepage_url,
        instagram_source_url=instagram_source_url,
        phone_source_url=phone_url,
        decision_maker_name="",
        decision_maker_source_url="",
        confidence_score=confidence,
        action_class="A_APPROVED",
        best_first_contact_channel=best_first_contact_channel(contact),
        touristnettr_integration_point=integration_point,
        short_note=f"Email-ready hotel lead. Source-valid hotel email found; decision-maker not required. Checked {len(checked_urls)} page(s).",
        reason_for_fit=fit_reason,
        validation_notes=validation_notes,
    )
    return lead, {"reason": "accepted", "website": website, "pages_checked": str(len(checked_urls))}


def load_seed_prospects(seed_file: Path) -> list[Prospect]:
    prospects: list[Prospect] = []
    if not seed_file.exists():
        return prospects
    with seed_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            website = normalize_url(row.get("website", ""))
            hotel_name = (row.get("hotel_name") or row.get("name") or domain_of(website)).strip()
            if not website or not hotel_name:
                continue
            prospects.append(Prospect(
                hotel_name=hotel_name,
                city=(row.get("city") or "").strip(),
                website=website,
                segment=(row.get("segment") or row.get("hotel_type_or_segment") or "").strip(),
                instagram=(row.get("instagram") or "").strip(),
                source="seed",
            ))
    return dedupe_prospects(prospects)


def dedupe_prospects(prospects: list[Prospect]) -> list[Prospect]:
    out, seen = [], set()
    for p in prospects:
        key = (registered_domain(domain_of(p.website)), norm(p.hotel_name), norm(p.city))
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def brave_discovery(query_file: Path, max_results_per_query: int) -> list[Prospect]:
    token = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not token or not query_file.exists():
        return []
    prospects: list[Prospect] = []
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "X-Subscription-Token": token, "User-Agent": "TouristNetTRLeadCrawler/1.1"})
    with query_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = (row.get("query") or "").strip()
            if not query:
                continue
            try:
                resp = session.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": min(max_results_per_query, 20), "country": "TR"},
                    timeout=20,
                )
                if resp.status_code >= 400:
                    continue
                data = resp.json()
            except Exception:
                continue
            for item in data.get("web", {}).get("results", []):
                url = item.get("url") or ""
                title = item.get("title") or ""
                if not url:
                    continue
                domain = domain_of(url)
                if not domain or any(bad in domain for bad in TRAVEL_BOOKING_DOMAINS):
                    continue
                clean_title = BeautifulSoup(title, "lxml").get_text(" ", strip=True)
                clean_title = re.sub(r"\s+\|.*$|\s+-\s+.*$", "", clean_title).strip()
                prospects.append(Prospect(
                    hotel_name=clean_title or domain,
                    city=(row.get("city") or "").strip(),
                    website=url,
                    segment=(row.get("segment") or "").strip(),
                    source="brave",
                ))
            time.sleep(1)
    return dedupe_prospects(prospects)


def load_suppression_index() -> SuppressionIndex:
    index = SuppressionIndex()
    for csv_path in list((ROOT / "leads").glob("**/*.csv")) + list((ROOT / "test-runs").glob("**/*.csv")):
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    index.add_row(row)
        except Exception:
            continue
    return index


def md_escape(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ")


def write_output_files(leads: list[Lead], stats: dict[str, object], run_date: str, target_count: int) -> tuple[Path, Path]:
    lead_dir = ROOT / "leads" / "hotel-daily" / run_date
    report_dir = ROOT / "reports" / "hotel-daily" / run_date
    lead_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    csv_path = lead_dir / f"today_action_{target_count}.csv"
    md_path = report_dir / "brief.md"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead.to_row())

    reason_counts: Counter = stats.get("reason_counts", Counter())  # type: ignore[assignment]
    channel_counts = Counter(lead.best_first_contact_channel for lead in leads)
    city_counts = Counter((lead.city or "unknown") for lead in leads)

    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# TouristNetTR Daily Hotel Email Leads — {run_date}\n\n")
        f.write("## Summary\n")
        f.write(f"- Target daily leads: {target_count}\n")
        f.write(f"- Email-ready hotel leads produced: {len(leads)}\n")
        f.write(f"- Prospects touched: {stats.get('prospects_touched', 0)}\n")
        f.write(f"- Seed prospects loaded: {stats.get('seed_count', 0)}\n")
        f.write(f"- Discovery prospects loaded: {stats.get('discovery_count', 0)}\n")
        f.write(f"- Duplicates skipped: {stats.get('duplicates_skipped', 0)}\n")
        f.write(f"- Rejected / blocked records: {stats.get('rejected_total', 0)}\n\n")
        f.write("## Rule Set\n")
        f.write("- Decision-maker data is optional.\n")
        f.write("- Phone/WhatsApp is optional.\n")
        f.write("- Source-valid hotel email is required.\n")
        f.write("- General hotel emails such as info@, reservation@, sales@, booking@ and contact@ are accepted when found on a relevant source page.\n")
        f.write("- No guessed or pattern-generated emails are accepted.\n\n")
        f.write("## Contact Channel Mix\n")
        if channel_counts:
            for channel, count in channel_counts.most_common():
                f.write(f"- {channel}: {count}\n")
        else:
            f.write("- No approved leads.\n")
        f.write("\n## City Mix\n")
        if city_counts:
            for city, count in city_counts.most_common():
                f.write(f"- {city}: {count}\n")
        else:
            f.write("- No approved leads.\n")
        f.write("\n## Final Leads\n\n")
        f.write("| hotel_name | city | segment | email | phone | website | score |\n")
        f.write("|---|---|---|---|---|---|---:|\n")
        for lead in leads:
            f.write(f"| {md_escape(lead.hotel_name)} | {md_escape(lead.city)} | {md_escape(lead.hotel_type_or_segment)} | {md_escape(lead.verified_email)} | {md_escape(lead.phone)} | {md_escape(lead.website)} | {lead.confidence_score} |\n")
        f.write("\n## Rejection / Blocker Counts\n")
        if reason_counts:
            for reason, count in reason_counts.most_common():
                f.write(f"- {reason}: {count}\n")
        else:
            f.write("- No rejection counts.\n")
    return csv_path, md_path


def read_lanes(query_file: Path) -> list[str]:
    lanes = []
    if query_file.exists():
        with query_file.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                city = (row.get("city") or "").strip()
                segment = (row.get("segment") or "").strip()
                query = (row.get("query") or "").strip()
                if city or segment:
                    lanes.append(f"{city} — {segment}".strip(" —"))
                elif query:
                    lanes.append(query)
    return lanes or [
        "Antalya — boutique / beach / resort",
        "Istanbul — boutique / city",
        "Cappadocia — cave / boutique",
        "Muğla / Bodrum / Fethiye — boutique / beach",
        "İzmir / Çeşme / Alaçatı — boutique / resort",
    ]


def write_zero_report(stats: dict[str, object], run_date: str, target_count: int) -> Path:
    report_dir = ROOT / "reports" / "failures" / run_date
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"hotel_daily_zero_email_leads_{run_date}.md"
    reason_counts: Counter = stats.get("reason_counts", Counter())  # type: ignore[assignment]
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# TouristNetTR Daily Hotel Lead Run — {run_date}\n\n")
        f.write("## Result\n\n")
        f.write("**Status:** No email-ready hotel lead was produced.\n\n")
        f.write(f"Target was {target_count}, but the relaxed daily chain still found 0 approved source-valid hotel emails.\n\n")
        f.write("## Coverage\n")
        f.write(f"- Seed prospects loaded: {stats.get('seed_count', 0)}\n")
        f.write(f"- Discovery prospects loaded: {stats.get('discovery_count', 0)}\n")
        f.write(f"- Prospects touched: {stats.get('prospects_touched', 0)}\n")
        f.write(f"- Pages checked: {stats.get('pages_checked', 0)}\n")
        f.write(f"- Duplicates skipped: {stats.get('duplicates_skipped', 0)}\n\n")
        f.write("## Configured lanes\n")
        for lane in stats.get("lanes", []):
            f.write(f"- {lane}\n")
        f.write("\n## Rejection / blocker counts\n")
        if reason_counts:
            for reason, count in reason_counts.most_common():
                f.write(f"- {reason}: {count}\n")
        else:
            f.write("- No prospects were processed far enough to produce rejection categories.\n")
        f.write("\n## Fix\n")
        f.write("Add more official hotel domains to `seeds/hotel_seed_domains.csv` or confirm `BRAVE_SEARCH_API_KEY` is configured.\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-count", type=int, default=10)
    parser.add_argument("--seed-file", type=Path, default=DEFAULT_SEED_FILE)
    parser.add_argument("--query-file", type=Path, default=DEFAULT_QUERY_FILE)
    parser.add_argument("--max-pages-per-site", type=int, default=int(os.getenv("MAX_PAGES_PER_SITE", "6")))
    parser.add_argument("--sleep-seconds", type=float, default=float(os.getenv("CRAWL_SLEEP_SECONDS", "0.25")))
    parser.add_argument("--max-prospects", type=int, default=int(os.getenv("MAX_PROSPECTS", "1000")))
    parser.add_argument("--brave-results-per-query", type=int, default=int(os.getenv("BRAVE_RESULTS_PER_QUERY", "10")))
    parser.add_argument("--min-confidence", type=int, default=int(os.getenv("MIN_CONFIDENCE", "70")))
    args = parser.parse_args()

    run_date = now_istanbul_date()
    stats: dict[str, object] = {
        "reason_counts": Counter(),
        "source_families": [
            "Seed CSV official domains",
            "Official hotel pages and internal contact/iletisim/reservation/KVKK pages",
            "Cloudflare data-cfemail extraction from official HTML",
            "Optional Brave Search API discovery when BRAVE_SEARCH_API_KEY is configured",
        ],
        "lanes": read_lanes(args.query_file),
    }
    seed_prospects = load_seed_prospects(args.seed_file)
    discovery_prospects = brave_discovery(args.query_file, args.brave_results_per_query)
    prospects = dedupe_prospects(seed_prospects + discovery_prospects)[: args.max_prospects]
    stats["seed_count"] = len(seed_prospects)
    stats["discovery_count"] = len(discovery_prospects)
    stats["prospect_count"] = len(prospects)

    suppression = load_suppression_index()
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 TouristNetTRHotelLeadCrawler/1.1 (+https://github.com/yasarcamus/mailleads)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    leads: list[Lead] = []
    reason_counts: Counter = stats["reason_counts"]  # type: ignore[assignment]
    duplicates_skipped = 0
    pages_checked = 0

    for prospect in prospects:
        if len(leads) >= args.target_count:
            break
        stats["prospects_touched"] = int(stats.get("prospects_touched", 0)) + 1
        lead, detail = inspect_prospect(session, prospect, args.max_pages_per_site, args.sleep_seconds, args.min_confidence)
        pages_checked += int(detail.get("pages_checked", "0") or 0)
        if lead is None:
            reason_counts[detail.get("reason", "unknown_reject")] += 1
            continue
        contact = ExtractedContact(email=lead.verified_email, phone=lead.phone, instagram=lead.instagram)
        if suppression.is_duplicate(prospect, contact, lead.lead_id):
            duplicates_skipped += 1
            reason_counts["duplicate_previous_output"] += 1
            continue
        lead_key = (lead.lead_id, norm_email(lead.verified_email), registered_domain(domain_of(lead.website)))
        existing_keys = {(x.lead_id, norm_email(x.verified_email), registered_domain(domain_of(x.website))) for x in leads}
        if lead_key in existing_keys:
            duplicates_skipped += 1
            reason_counts["duplicate_current_run"] += 1
            continue
        leads.append(lead)

    stats["pages_checked"] = pages_checked
    stats["accepted_count"] = len(leads)
    stats["duplicates_skipped"] = duplicates_skipped
    stats["rejected_total"] = sum(reason_counts.values())
    stats["guessed_emails_rejected"] = "all inferred/pattern emails blocked by design"

    if leads:
        csv_path, md_path = write_output_files(leads, stats, run_date, args.target_count)
        print(f"SUCCESS: wrote {csv_path.relative_to(ROOT)} and {md_path.relative_to(ROOT)}")
        if len(leads) < args.target_count:
            print(f"WARNING: produced {len(leads)}/{args.target_count}; committed partial daily output instead of failing the run.")
    else:
        failure_path = write_zero_report(stats, run_date, args.target_count)
        print(f"ZERO_LEADS: wrote {failure_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
