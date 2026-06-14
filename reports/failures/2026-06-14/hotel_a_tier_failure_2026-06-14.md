# TouristNetTR Hotel A-Tier Lead Production Failure Report — 2026-06-14

## Result

**Status:** FAILED — no CSV lead file committed.

The run did **not** produce exactly 145 new, verified, sendable A-tier hotel leads. Per protocol, no partial or weak lead file was committed.

## Verified A-tier count found

**0 verified A-tier hotel leads committed.**

This does not mean there are no suitable hotels in Türkiye. It means this run could not honestly complete the full A-tier validation chain at production standard within the available tool path.

## Prospect research coverage attempted

The run attempted broad discovery across the required hotel-only lanes instead of stopping on one chain or one directory.

### City / segment lanes attempted

1. Antalya — resort, beach, boutique hotels
2. Istanbul — boutique, city, luxury hotels
3. Cappadocia / Göreme / Ürgüp / Uçhisar — cave and boutique hotels
4. Muğla / Bodrum / Marmaris / Fethiye / Datça — resort and boutique hotels
5. İzmir / Çeşme / Alaçatı — boutique and resort hotels
6. Bursa / Afyon / Denizli / Pamukkale — thermal and city hotels
7. Trabzon / Rize / Sapanca / Bolu — nature and boutique hotels
8. Ankara / Konya / Gaziantep / Mardin — city and boutique hotels

### Source families attempted

- Public web search for city + hotel + contact/email combinations
- Turkish search patterns using `otel`, `iletişim`, `e-posta`, `email`
- English search patterns using `hotel`, `contact`, `email`, `official site`
- Official-site oriented search patterns
- Segment-specific discovery patterns: resort, boutique, thermal, cave, city hotels
- GitHub repository access check for write permission and output path readiness

## Queries / lanes tested

Representative discovery queries included:

- `Antalya resort hotel iletişim email`
- `Istanbul boutique hotel contact email`
- `Cappadocia cave hotel contact email`
- `Bodrum boutique hotel contact email`
- `Çeşme Alaçatı boutique hotel iletişim e-mail`
- `Afyon thermal hotel iletişim email`
- `Trabzon boutique hotel iletişim email`
- `Mardin boutique hotel iletişim email`
- `site:.com.tr Antalya otel iletişim e-posta`
- `site:.com.tr İstanbul otel iletişim e-posta`
- `site:.com.tr Göreme otel iletişim e-posta`
- `site:.com.tr Bodrum otel iletişim e-posta`
- `Antalya hotel contact email official site`
- `Istanbul hotel contact email official site`
- `Goreme cave hotel contact email official site`
- `Bodrum hotel contact email official site`

## Why 145 could not be reached

The run failed for operational reasons, not because the market lacks leads.

Main blockers:

1. **Search retrieval quality was too poor for production extraction.** Several broad and targeted search queries returned empty or irrelevant results rather than usable hotel contact pages.
2. **The run could not honestly inspect 300–750 prospects.** The discovery stage did not yield enough reliable official hotel pages to begin large-scale validation.
3. **A-tier requires exact email source URLs and phone source URLs.** Without inspecting official/contact/footer/KVKK/reservation pages per hotel, committing rows would have required guesswork.
4. **Email inference is forbidden.** The obvious shortcut of generating `info@`, `reservation@`, or similar hotel emails was correctly rejected.
5. **Deliverability risk would be high if partial scraped/directory data were promoted.** That would repeat the bounce problem this process is designed to eliminate.

## What was correctly avoided

- No guessed emails were created.
- No `info@domain` style fabricated addresses were used.
- No phone-only or form-only hotels were promoted.
- No non-hotel categories were mixed in.
- No weak partial CSV was committed as if it were a successful 145-lead production file.

## Categories that blocked the target

The main blocker was not hotel fit. It was **source-verifiable contact extraction** at scale.

Common expected blockers in this category:

- Hotels using contact forms instead of public email
- Emails hidden behind JavaScript or anti-scraping layers
- Cloudflare-protected pages requiring HTML-level extraction
- Directory listings with incomplete or mismatched contact fields
- Hotel group pages where property-level email is not visible
- Old hotel pages with stale emails and weak source confidence

## Next expansion path

The next run should not rely on broad web search alone. It should use a more deterministic prospect pipeline:

1. Build prospect pools from official tourism directories, regional hotel associations, Google Business profiles, hotel maps, and booking/meta-search names.
2. For each hotel, open the official website directly.
3. Crawl `/contact`, `/iletisim`, `/reservation`, `/kvkk`, footer, header, and property/group pages.
4. Decode Cloudflare `data-cfemail` from official HTML where present.
5. Extract phone and email only from source-valid pages.
6. Keep a rejection log separate from final lead files.
7. Commit only when the final CSV has exactly 145 rows passing all seven validation passes.

## Recommended operating model

A realistic production model is city-batch execution:

- Antalya batch
- Cappadocia batch
- Muğla / Bodrum / Fethiye batch
- İstanbul boutique/city batch
- İzmir / Çeşme / Alaçatı batch
- Bursa / Afyon / Denizli thermal batch
- Trabzon / Rize / Sapanca / Bolu nature-hotel batch
- Ankara / Konya / Gaziantep / Mardin city-boutique batch

This keeps quality high without forcing weak rows into the CSV.

## Final decision

**No lead CSV committed.**

The correct output for this run is this failure report. The task should be rerun with a stronger deterministic crawler/source pipeline before attempting a 145-row A-tier CSV commit.