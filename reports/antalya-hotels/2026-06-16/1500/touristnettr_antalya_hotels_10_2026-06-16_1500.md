# TouristNetTR Antalya hotel leads — 10 record run

## Result

- Output committed: yes
- CSV rows: 10
- Repository: `yasarcamus/mailleads`
- CSV path: `leads/antalya-hotels/2026-06-16/1500/touristnettr_antalya_hotels_10_2026-06-16_1500.csv`

## Integrity posture

This run produced exactly 10 new Antalya hotel prospects without fabricating email addresses.

Emails were **not** guessed. No `info@`, `reservation@`, `sales@`, `booking@`, or similar mailbox was inserted unless source-visible verification existed. In this pass, no source-visible email could be captured for the accepted new records, so the `verified_email` fields are blank and the `email_status` values are marked as website-only.

Phone fields were also left blank unless an exact source-visible phone was captured.

## Deduplication baseline

Checked against known existing Antalya-related repository records:

- `leads/antalya-hotels-bulk/2026-06-16/0048/touristnettr_antalya_hotels_bulk_2026-06-16_0048.csv`
- `leads/hotel-a-tier/2026-06-14/qa/touristnettr_hotels_a_tier_qa_full_2026-06-14.csv`
- Existing Antalya A-tier record excluded: Alhambra Residence / `alhambraaparthotel.com` / `info@alhambraaparthotel.com`

The 10 accepted records are outside the prior Antalya bulk list by hotel name and domain.

## Coverage

Accepted records cover multiple Antalya segments:

- Kaleiçi / Muratpaşa boutique and small hotels
- Antalya city / Muratpaşa boutique and 4-star city hotels
- Lara / Muratpaşa boutique and 3-star beach-area hotels

## Records

| # | Hotel | Area | Segment | Website | Email status |
|---:|---|---|---|---|---|
| 1 | Sibel Hotel | Kaleiçi / Muratpaşa | Boutique hotel | https://www.sibelhotel.com/ | Website-only; no verified published email captured |
| 2 | Kauçuk Hotel | Kaleiçi / Muratpaşa | Boutique hotel | https://www.kaucukhotel.com/ | Website-only; no verified published email captured |
| 3 | Cedrus Hotel | Kaleiçi / Muratpaşa | Boutique hotel | https://www.cedrus-hotel.com/ | Website-only; no verified published email captured |
| 4 | Casa Sur Antalya | Kaleiçi / Muratpaşa | Boutique hotel | https://www.casasurantalya.com/ | Website-only; no verified published email captured |
| 5 | Perge Hotels | Muratpaşa / Antalya city | Boutique / 4-star | https://www.pergehotels.com/ | Website-only; no verified published email captured |
| 6 | Mono Hotel | Kaleiçi / Muratpaşa | Small boutique hotel | https://www.monohotel.com.tr/ | Website-only; no verified published email captured |
| 7 | Mai İnci Hotel | Muratpaşa / Antalya city | 4-star city hotel | https://www.maiincihotel.com/ | Website-only; no verified published email captured |
| 8 | Afflon Hotels Loft City | Muratpaşa / Antalya city | Boutique/city hotel | https://www.afflonhotels.com/ | Website-only; no verified published email captured |
| 9 | Esperanza Boutique Hotel | Lara / Muratpaşa | Boutique hotel | https://www.esperanzahotel.com/ | Website-only; no verified published email captured |
| 10 | Lara Park Hotel | Lara / Muratpaşa | 3-star hotel | https://www.laraparkhotel.com/ | Website-only; no verified published email captured |

## Next enrichment action

Run a strict enrichment pass on these 10 domains and only promote emails when they are visibly published, present in `mailto:`, extracted from page HTML, decoded from Cloudflare `data-cfemail`, or verified by a matching trusted source. Do not backfill guessed generic mailboxes.
