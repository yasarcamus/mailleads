# TouristNetTR Antalya email-ready hotel leads — failure report

Run date: 2026-06-16 12:30 Europe/Istanbul

## Result

Could not honestly produce exactly 10 new Antalya hotel records with verified, source-visible email addresses in this run.

No CSV was committed because the hard target requires every final record to include a verified email, and padding with guessed addresses is explicitly forbidden.

## What was checked

### Repository dedupe baseline

Checked existing `yasarcamus/mailleads` Antalya/hotel files before accepting any new record:

- `leads/antalya-hotels-bulk/2026-06-16/0048/touristnettr_antalya_hotels_bulk_2026-06-16_0048.csv`
- `leads/hotel-a-tier/2026-06-14/qa/touristnettr_hotels_a_tier_qa_full_2026-06-14.csv`

Known existing Antalya-related record detected and excluded from reuse:

- Alhambra Residence / `alhambraaparthotel.com` / `info@alhambraaparthotel.com`

Known Antalya bulk candidates already present as website-only/no-email records were not reused as final email-ready records unless a new verified email could be captured.

### Search expansion attempted

Searched multiple Antalya segments and query shapes, including:

- Kaleiçi / Muratpaşa boutique hotels
- Konyaaltı apart hotels
- Kemer boutique hotels
- Alanya boutique hotels
- Generic Antalya hotel contact/email queries
- Domain-level checks for candidate official sites from the previous Antalya bulk list

Candidate examples checked from the existing Antalya bulk base:

- Bacchus Pension
- Sabah Pension
- Villa Tulipan
- Urcu Hotel
- Puding Hotel
- Tuvana Hotel
- Adalya Port Hotel
- Hotel 1207

## Blockers

- Search results did not expose enough official contact pages or email-visible pages.
- Direct official-site fetches for several candidate domains failed through the available browsing layer with cache/safety fetch errors.
- Because emails could not be source-verified, no candidate could be promoted into the final email-ready CSV.

## Integrity decision

I did not fabricate `info@`, `reservation@`, `sales@`, or any other generic mailbox.

I did not create a partial CSV because the job definition requires the final CSV to contain exactly 10 valid email-ready records whenever honestly possible, and otherwise to commit a failure report.

## Next expansion path

For the next run, expand via pages that are more likely to expose static contact details:

1. Official hotel websites with `/contact`, `/iletisim`, `/contact-us`, `/tr/iletisim`, and `/en/contact` paths.
2. Small hotel directories that mirror official email addresses, then verify against official domains where possible.
3. District-by-district scrape order: Kaleiçi → Konyaaltı → Kemer → Çıralı/Olympos → Kaş/Kalkan → Alanya → Side/Manavgat.
4. Prioritize candidates whose sites use visible `mailto:` links or Cloudflare `data-cfemail` blocks.

## Status

Failure report committed instead of unsafe lead padding.
