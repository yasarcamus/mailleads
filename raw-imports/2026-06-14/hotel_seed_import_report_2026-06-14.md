# Hotel Domain Seed Import Report — 2026-06-14

## Result

Uploaded lead files were processed and reduced into a crawler-ready hotel-domain seed payload.

## Counts

- Total input rows scanned: 9,983
- Raw hotel-like records with usable website/domain: 2,905
- Unique crawler seed rows created: 1,265
- Unique base domains in final seed: 926
- Hotel-like records without usable website/domain: 2,676
- Non-hotel / acente / transfer / unclear quarantine rows: 4,402
- Previous mailed suppression rows detected: 609
- Uploaded input files scanned: 15

## Active seed payload

The active hotel seed CSV is stored as gzip+base64 parts under:

```text
seeds/payloads/hotel_seed_domains_2026-06-14.csv.gz.b64.part01
...
seeds/payloads/hotel_seed_domains_2026-06-14.csv.gz.b64.part08
```

Before every GitHub Actions run, `scripts/materialize_seed_payloads.py` concatenates these parts, decodes them, and writes:

```text
seeds/hotel_seed_domains.csv
```

The crawler then reads the materialized CSV normally.

## Rule used

Only hotel-like records with a usable website/domain were moved into the active crawler seed. Acente, transfer, restaurant, generic business, money transfer, real estate/property/villa, transportation and unrelated categories were excluded from the active hotel seed.

## Why compressed payload parts?

The seed contains 1,265 rows. It is stored as split compressed payloads to avoid large GitHub connector writes while still preserving the full seed and allowing deterministic materialization inside GitHub Actions.

## Next step

Run the workflow manually from GitHub Actions:

```text
Actions → TouristNetTR Hotel Lead Runner → Run workflow
```

Suggested test parameters:

```text
target_count = 50
max_prospects = 1265
max_pages_per_site = 8
```

If the 50-lead test succeeds, increase `target_count` to 145.
