# TouristNetTR Antalya Hotels Bulk Lead Run

## Result

- Output committed: yes
- CSV rows: 50
- Target: up to 200
- Repository: yasarcamus/mailleads
- CSV path: `leads/antalya-hotels-bulk/2026-06-16/0048/touristnettr_antalya_hotels_bulk_2026-06-16_0048.csv`

## Why this run stopped below 200

The run did not honestly reach 200 validated leads. Live search and page-access tooling returned sparse/failed discovery results for broad Antalya hotel queries, and repository-wide historical deduplication could not be completed from the available connector surface. Rather than fabricate emails, phone numbers, or force weak rows, the run committed a conservative partial dataset.

## Validation posture

- Emails were left blank unless a verified published email could be captured.
- No generic `info@`, `reservation@`, or guessed mailbox was created.
- Phone fields were left blank unless an exact phone source was captured.
- Each row is unique within this run by hotel name and website/domain.
- Rows are limited to Antalya areas and target segments: boutique hotels, apart hotels, small hotels, 3-star/4-star city or beach hotels, and foreign-tourist-facing pensions.
- Obvious 5-star mega-resorts, agencies, DMCs, transfer firms, villa rental/property-management firms, restaurants, clinics, shops, and unrelated businesses were excluded.

## Coverage included

- Kaleiçi / Muratpaşa
- Konyaaltı
- Lara / Muratpaşa
- Alanya
- Kemer
- Kaş
- Kalkan
- Çıralı
- Side / Manavgat
- Belek

## Next pass recommendation

Run a stricter enrichment pass against this CSV:

1. Visit each official website/contact page.
2. Extract visible emails, mailto links, Cloudflare `data-cfemail`, phones, and Instagram links.
3. Drop any row whose website/domain cannot be confirmed as official.
4. Then expand district-by-district until 200 strong rows are reached.

## Notes

This is a partial but usable prospect base, not a final 200-row verified email file. The key constraint was avoiding fabricated contact data.