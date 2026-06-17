# TouristNetTR Antalya hotel leads - 2026-06-17 1500

## Status

SUCCESS - 10 Antalya hotel lead records committed.

## Output

- CSV: `leads/antalya-hotels/2026-06-17/1500/touristnettr_antalya_hotels_10_2026-06-17_1500.csv`
- Row count: 10

## Scope applied

Included Antalya province hotel/accommodation businesses matching the requested pool: boutique hotels, small old-town hotels, and special-class hotel-style accommodation. Excluded villa rental, property management, agencies, restaurants-only businesses, clinics, shops, and mega resort targets.

## Records

| # | Hotel | Area | Segment | Email status | Primary channel | Source |
|---:|---|---|---|---|---|---|
| 1 | Aspen Hotel Kaleiçi | Muratpaşa / Kaleiçi | Boutique hotel | verified | email | https://www.aspenhotel.com.tr/contact |
| 2 | Puding Hotel | Muratpaşa / Kaleiçi | Boutique hotel | verified | email | https://pudinghotel.com/ |
| 3 | Tuvana Hotel | Muratpaşa / Kaleiçi | Boutique hotel | verified | email | https://tuvanahotel.com/ |
| 4 | Elegance East Hotel | Muratpaşa / Kaleiçi | Boutique hotel | verified | email | https://www.eleganceeasthotel.com/ |
| 5 | Minyon Hotel | Muratpaşa / Kaleiçi | Boutique hotel | website-only | phone | https://www.minyonhotel.com/ |
| 6 | Doğan Hotel | Muratpaşa / Kaleiçi | Boutique hotel | verified | email | https://doganhotel.com/ |
| 7 | Alp Paşa Hotel | Muratpaşa / Kaleiçi | Boutique / historic hotel | verified | email | https://alppasa.com/tr/ |
| 8 | Hotel 1207 Special Class | Muratpaşa / Kaleiçi | Special class hotel | website-only | website | https://www.hotel1207.com/ |
| 9 | White Garden Hotel | Muratpaşa / Kaleiçi | Boutique hotel | website-only | website | https://www.whitegardenhotel.com/ |
| 10 | Castle Old Town | Muratpaşa / Kaleiçi | Old-town small hotel | website-only | phone | https://www.castleoldtown.com/ |

## Validation notes

- Email values were only copied when visible as exact text on an official hotel page.
- Cloudflare-protected or parser-redacted emails were not copied into `verified_email`.
- Website-only records remain usable for first contact by website or phone, but should not be treated as email-ready.
- Multi-district expansion was attempted toward Kaş, Alanya, Lara, and Kemer-style hotel targets; accessible official pages with source-visible data were weaker than Kaleiçi in this run, so the final set uses the strongest validated Antalya hotel records found.
- Repository write access was verified by creating the CSV and this report directly in `yasarcamus/mailleads`.

## Dedupe notes

Deduplication keys considered for this run: hotel name, domain, phone, Instagram, and email. No duplicate was knowingly introduced inside this batch. Full historical repository-tree enumeration was not exposed by the available GitHub connector in this run, so the report avoids claiming complete historical dedupe beyond the current validated batch and previously known target exclusions.
