#!/usr/bin/env python3
"""Checkpointed domain email extractor for TouristNetTR.

Reads domain/website rows, crawls official pages, extracts source-visible emails,
and writes progress after every domain so a broken GitHub Actions run does not
trash the whole batch.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import html
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+-])([A-Z0-9._%+\-]{1,64}@[A-Z0-9.\-]{2,255}\.[A-Z]{2,24})(?![A-Z0-9._%+-])")
CFEMAIL_RE = re.compile(r'data-cfemail=["\']([0-9a-fA-F]+)["\']')
CFEMAIL_HASH_RE = re.compile(r"/cdn-cgi/l/email-protection#([0-9a-fA-F]+)")

CONTACT_KEYWORDS = (
    "contact", "iletisim", "iletişim", "reservation", "rezervasyon", "booking",
    "kvkk", "kurumsal", "corporate", "about", "hakkimizda", "hakkımızda",
    "sales", "satis", "satış", "guest", "misafir", "frontoffice", "front-office",
    "reception", "privacy", "policy",
)
FALLBACK_PATHS = (
    "/contact", "/contact-us", "/contacts", "/iletisim", "/iletişim", "/tr/iletisim",
    "/tr/iletişim", "/kurumsal", "/hakkimizda", "/hakkımızda", "/about", "/about-us",
    "/reservation", "/reservations", "/rezervasyon", "/booking", "/sales", "/kvkk",
    "/privacy-policy", "/privacy", "/contact.html", "/iletisim.html",
)
NOISE_EMAIL_DOMAINS = {
    "example.com", "domain.com", "sentry.io", "wix.com", "wordpress.com", "schema.org",
    "w3.org", "google.com", "googlemail.com", "cloudflare.com", "facebook.com",
    "instagram.com", "booking.com", "tripadvisor.com", "expedia.com", "agoda.com",
}
PLATFORM_DOMAINS = (
    "instagram.com", "facebook.com", "booking.com", "tripadvisor.", "expedia.", "agoda.",
    "hotels.com", "trivago.", "sahibinden.com", "airbnb.", "google.com", "maps.google.",
    "wa.me", "whatsapp.com", "linktr.ee", "beacons.ai", "youtube.com", "youtu.be",
)
COMMON_FREE_EMAIL_DOMAINS = {
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yandex.com", "icloud.com", "live.com"
}
BUSINESS_LOCALS = {
    "reservation": 30, "reservations": 30, "booking": 28, "sales": 26, "info": 24,
    "contact": 20, "reception": 18, "frontoffice": 18, "front.office": 18,
    "guestrelations": 17, "guest.relations": 17, "hello": 12, "mail": 10,
}
INPUT_COLUMNS = (
    "business_name", "hotel_name", "company_name", "name", "title", "city", "category",
    "segment", "website", "domain", "url", "source_url", "google_maps_url", "place_id",
)
RESULT_COLUMNS = [
    "processed_at", "status", "business_name", "city", "category", "website", "domain",
    "best_email", "all_emails", "email_source_url", "pages_checked", "checked_urls",
    "reason", "source_url", "google_maps_url", "place_id",
]
FOUND_COLUMNS = [
    "processed_at", "business_name", "city", "category", "website", "domain",
    "best_email", "all_emails", "email_source_url", "pages_checked", "source_url",
    "google_maps_url", "place_id",
]


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "").strip().lower())


def normalize_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if "@" in value and "://" not in value:
        value = value.split("@", 1)[1]
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    return value


def domain_of(value: str) -> str:
    value = (value or "").strip().lower()
    if not value:
        return ""
    if "@" in value and "://" not in value:
        host = value.split("@", 1)[1]
    else:
        parsed = urlparse(normalize_url(value))
        host = parsed.netloc or parsed.path.split("/", 1)[0]
    host = host.split("@")[ -1].split(":", 1)[0].strip("./")
    if host.startswith("www."):
        host = host[4:]
    return host


def registered_domain(domain: str) -> str:
    d = domain_of(domain) if "://" in domain or "/" in domain else (domain or "").lower().strip(".")
    parts = [p for p in d.split(".") if p]
    if len(parts) <= 2:
        return d
    second_level_cc = {"com", "net", "org", "edu", "gov", "bel", "k12", "av", "gen", "web"}
    if len(parts) >= 3 and parts[-1] == "tr" and parts[-2] in second_level_cc:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_platform_domain(domain: str) -> bool:
    d = domain_of(domain)
    return any(bad in d for bad in PLATFORM_DOMAINS)


def clean_email(email: str) -> str:
    return norm(email).replace("mailto:", "").split("?", 1)[0].strip("<>.,;:()[]{}\\'\"")


def decode_cfemail(encoded: str) -> str:
    try:
        data = bytes.fromhex(encoded)
        key = data[0]
        return "".join(chr(b ^ key) for b in data[1:])
    except Exception:
        return ""


def is_noise_email(email: str) -> bool:
    email = clean_email(email)
    if not email or "@" not in email:
        return True
    local, domain = email.rsplit("@", 1)
    domain = domain_of(domain)
    if domain in NOISE_EMAIL_DOMAINS:
        return True
    if local in {"example", "test", "yourname", "name", "email", "mail"}:
        return True
    if any(email.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf")):
        return True
    return False


def extract_emails(raw_html: str, soup: BeautifulSoup) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = html.unescape(a.get("href", ""))
        if href.lower().startswith("mailto:"):
            email = clean_email(href.split(":", 1)[1])
            if not is_noise_email(email):
                found.append((email, "mailto"))
    for m in EMAIL_RE.finditer(html.unescape(raw_html)):
        email = clean_email(m.group(1))
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


def request_get(session: requests.Session, url: str, timeout: int) -> Optional[requests.Response]:
    candidates = [normalize_url(url)]
    if candidates[0].startswith("https://"):
        candidates.append("http://" + candidates[0][8:])
    for candidate in candidates:
        try:
            resp = session.get(candidate, timeout=timeout, allow_redirects=True)
            if resp.status_code >= 400:
                continue
            ctype = resp.headers.get("content-type", "").lower()
            if ctype and "html" not in ctype and "xhtml" not in ctype:
                continue
            return resp
        except requests.RequestException:
            continue
    return None


def contact_links(base_url: str, soup: BeautifulSoup, max_links: int) -> list[str]:
    base_reg = registered_domain(domain_of(base_url))
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "tel:", "mailto:")):
            continue
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if registered_domain(domain_of(url)) != base_reg:
            continue
        hay = norm(url + " " + a.get_text(" ", strip=True))
        if any(k in hay for k in CONTACT_KEYWORDS):
            canonical = parsed._replace(fragment="", query="").geturl()
            if canonical not in seen:
                seen.add(canonical)
                out.append(canonical)
        if len(out) >= max_links:
            break
    return out


def candidate_urls(homepage_url: str, soup: BeautifulSoup, max_pages: int) -> list[str]:
    urls, seen = [], set()
    def add(u: str) -> None:
        if len(urls) >= max_pages:
            return
        parsed = urlparse(u)
        canonical = parsed._replace(fragment="", query="").geturl()
        if canonical not in seen:
            seen.add(canonical)
            urls.append(canonical)
    add(homepage_url)
    for u in contact_links(homepage_url, soup, max_pages - 1):
        add(u)
    for path in FALLBACK_PATHS:
        add(urljoin(homepage_url, path))
    return urls[:max_pages]


def pick_best_email(emails: Iterable[tuple[str, str, str]], official_domain: str) -> tuple[str, str, str]:
    items = list(emails)
    if not items:
        return "", "", ""
    official_reg = registered_domain(official_domain)
    def score(item: tuple[str, str, str]) -> int:
        email, source_url, kind = item
        local, domain = email.rsplit("@", 1)
        s = 0
        if registered_domain(domain) == official_reg:
            s += 60
        if registered_domain(domain_of(source_url)) == official_reg:
            s += 25
        s += {"cloudflare": 18, "mailto": 15, "html": 8}.get(kind, 0)
        s += BUSINESS_LOCALS.get(local.lower(), 0)
        if domain in COMMON_FREE_EMAIL_DOMAINS:
            s -= 10
        return s
    return max(items, key=score)


@dataclasses.dataclass
class DomainRow:
    business_name: str
    city: str
    category: str
    website: str
    domain: str
    source_url: str
    google_maps_url: str
    place_id: str


def read_input(path: Path) -> list[DomainRow]:
    rows: list[DomainRow] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            website = raw.get("website") or raw.get("url") or raw.get("domain") or ""
            domain = domain_of(raw.get("domain") or website)
            if not website and domain:
                website = domain
            if not domain:
                continue
            rows.append(DomainRow(
                business_name=(raw.get("business_name") or raw.get("hotel_name") or raw.get("company_name") or raw.get("name") or raw.get("title") or domain).strip(),
                city=(raw.get("city") or "").strip(),
                category=(raw.get("category") or raw.get("segment") or "").strip(),
                website=normalize_url(website),
                domain=domain,
                source_url=(raw.get("source_url") or "").strip(),
                google_maps_url=(raw.get("google_maps_url") or raw.get("maps_url") or "").strip(),
                place_id=(raw.get("place_id") or "").strip(),
            ))
    deduped, seen = [], set()
    for row in rows:
        key = registered_domain(row.domain) or row.domain
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def read_processed(result_path: Path) -> set[str]:
    if not result_path.exists():
        return set()
    processed = set()
    with result_path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            d = registered_domain(row.get("domain", ""))
            if d:
                processed.add(d)
    return processed


def ensure_csv(path: Path, columns: list[str]) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=columns).writeheader()


def append_row(path: Path, columns: list[str], row: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writerow(row)
        f.flush()
        os.fsync(f.fileno())


def write_checkpoint(path: Path, state: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def inspect_domain(session: requests.Session, row: DomainRow, max_pages: int, timeout: int, sleep_seconds: float) -> dict[str, str]:
    now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    base = {
        "processed_at": now,
        "business_name": row.business_name,
        "city": row.city,
        "category": row.category,
        "website": row.website,
        "domain": row.domain,
        "source_url": row.source_url,
        "google_maps_url": row.google_maps_url,
        "place_id": row.place_id,
    }
    if is_platform_domain(row.domain):
        return {**base, "status": "skipped", "reason": "blocked_platform_domain", "best_email": "", "all_emails": "", "email_source_url": "", "pages_checked": "0", "checked_urls": ""}

    resp = request_get(session, row.website, timeout)
    if resp is None:
        return {**base, "status": "failed", "reason": "homepage_fetch_failed", "best_email": "", "all_emails": "", "email_source_url": "", "pages_checked": "0", "checked_urls": ""}

    soup = BeautifulSoup(resp.text, "lxml")
    urls = candidate_urls(resp.url, soup, max_pages)
    official_reg = registered_domain(domain_of(resp.url))
    emails: list[tuple[str, str, str]] = []
    checked: list[str] = []

    for url in urls:
        if sleep_seconds:
            time.sleep(sleep_seconds)
        r = resp if url == resp.url else request_get(session, url, timeout)
        if r is None:
            continue
        checked.append(r.url)
        s = BeautifulSoup(r.text, "lxml")
        if registered_domain(domain_of(r.url)) != official_reg:
            continue
        for email, kind in extract_emails(r.text, s):
            emails.append((email, r.url, kind))

    deduped, seen = [], set()
    for email, url, kind in emails:
        if email not in seen:
            seen.add(email)
            deduped.append((email, url, kind))
    best_email, best_url, _kind = pick_best_email(deduped, official_reg)
    if not best_email:
        return {**base, "status": "no_email", "reason": "no_source_visible_email", "best_email": "", "all_emails": "", "email_source_url": "", "pages_checked": str(len(checked)), "checked_urls": " | ".join(checked[:12])}
    return {**base, "status": "found", "reason": "source_visible_email_found", "best_email": best_email, "all_emails": ";".join(e for e, _u, _k in deduped), "email_source_url": best_url, "pages_checked": str(len(checked)), "checked_urls": " | ".join(checked[:12])}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("seeds/domain_email_input.csv"))
    parser.add_argument("--run-dir", type=Path, default=Path("runs/domain-email/current"))
    parser.add_argument("--max-pages-per-site", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=18)
    parser.add_argument("--sleep-seconds", type=float, default=0.4)
    parser.add_argument("--stop-after", type=int, default=0, help="0 means no row count limit")
    parser.add_argument("--max-runtime-seconds", type=int, default=0, help="0 means no runtime limit")
    parser.add_argument("--fresh", action="store_true", help="Delete previous current run outputs before starting")
    args = parser.parse_args()

    if args.fresh and args.run_dir.exists():
        for p in ["all_results.csv", "emails_found.csv", "checkpoint.json"]:
            target = args.run_dir / p
            if target.exists():
                target.unlink()

    args.run_dir.mkdir(parents=True, exist_ok=True)
    all_results = args.run_dir / "all_results.csv"
    emails_found = args.run_dir / "emails_found.csv"
    checkpoint = args.run_dir / "checkpoint.json"
    ensure_csv(all_results, RESULT_COLUMNS)
    ensure_csv(emails_found, FOUND_COLUMNS)

    domains = read_input(args.input)
    processed = read_processed(all_results)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 TouristNetTRDomainEmailExtractor/1.0 (+https://github.com/yasarcamus/mailleads)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    start = time.monotonic()
    done_this_run = 0
    found_this_run = 0
    skipped_resume = 0

    for idx, row in enumerate(domains, start=1):
        reg = registered_domain(row.domain)
        if reg in processed:
            skipped_resume += 1
            continue
        if args.stop_after and done_this_run >= args.stop_after:
            break
        if args.max_runtime_seconds and time.monotonic() - start > args.max_runtime_seconds:
            print("MAX_RUNTIME_REACHED: clean exit before Actions timeout.")
            break
        try:
            result = inspect_domain(session, row, args.max_pages_per_site, args.timeout, args.sleep_seconds)
        except Exception as exc:  # keep the batch alive
            result = {
                "processed_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "status": "error", "reason": f"exception:{type(exc).__name__}:{str(exc)[:180]}",
                "business_name": row.business_name, "city": row.city, "category": row.category,
                "website": row.website, "domain": row.domain, "best_email": "", "all_emails": "",
                "email_source_url": "", "pages_checked": "0", "checked_urls": "",
                "source_url": row.source_url, "google_maps_url": row.google_maps_url, "place_id": row.place_id,
            }
        append_row(all_results, RESULT_COLUMNS, result)
        if result.get("status") == "found":
            append_row(emails_found, FOUND_COLUMNS, result)
            found_this_run += 1
        processed.add(reg)
        done_this_run += 1
        write_checkpoint(checkpoint, {
            "updated_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "input_file": str(args.input),
            "run_dir": str(args.run_dir),
            "total_input_unique_domains": len(domains),
            "processed_total": len(processed),
            "remaining_estimate": max(0, len(domains) - len(processed)),
            "done_this_run": done_this_run,
            "found_this_run": found_this_run,
            "skipped_resume": skipped_resume,
            "last_domain": row.domain,
            "last_status": result.get("status", ""),
        })
        print(f"[{idx}/{len(domains)}] {row.domain} -> {result.get('status')} {result.get('best_email','')}", flush=True)

    print(json.dumps({
        "input_unique_domains": len(domains),
        "processed_total": len(processed),
        "done_this_run": done_this_run,
        "found_this_run": found_this_run,
        "skipped_resume": skipped_resume,
        "all_results": str(all_results),
        "emails_found": str(emails_found),
        "checkpoint": str(checkpoint),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
