# TouristNetTR Hotel Lead Pipeline

Bu repo artık ChatGPT'in broad search yapıp failure dönmesine bağlı değil. Asıl üretim hattı GitHub Actions + Python crawler üzerinden çalışır.

## Dosyalar

```text
.github/workflows/hotel-leads.yml
scripts/hotel_lead_runner.py
seeds/hotel_seed_domains.csv
seeds/city_queries.csv
requirements.txt
```

## Çalışma mantığı

1. `seeds/hotel_seed_domains.csv` içindeki otel domainleri okunur.
2. Opsiyonel olarak `BRAVE_SEARCH_API_KEY` secret'ı varsa `seeds/city_queries.csv` üzerinden ek aday domainler bulunur.
3. Her otelin resmi sitesi açılır.
4. Homepage dışında contact / iletişim / reservation / KVKK / footer / corporate sayfaları taranır.
5. Email sadece kaynakta görünürse veya resmi HTML içinden extract edilirse kabul edilir.
6. Cloudflare `data-cfemail` decode edilir.
7. Telefon/WhatsApp kaynak URL ile doğrulanır.
8. Eski CSV ve test-run çıktıları üzerinden duplicate suppression yapılır.
9. Tam 145 A-tier lead varsa production CSV + Markdown rapor yazılır.
10. 145 yoksa zayıf CSV basılmaz; failure report yazılır.

## Başarılı output path'leri

```text
leads/hotel-a-tier/YYYY-MM-DD/touristnettr_hotels_a_tier_YYYY-MM-DD.csv
reports/hotel-a-tier/YYYY-MM-DD/touristnettr_hotels_a_tier_YYYY-MM-DD.md
```

## Failure output path'i

```text
reports/failures/YYYY-MM-DD/hotel_a_tier_failure_YYYY-MM-DD.md
```

## Seed formatı

`seeds/hotel_seed_domains.csv`:

```csv
hotel_name,city,website,segment,instagram
Example Hotel,Antalya,https://examplehotel.com,resort hotel,https://instagram.com/examplehotel
```

En güçlü sistem için bu dosyaya 500–2000 resmi otel domaini eklenmeli. Seed kalitesi yükseldikçe A-tier output yükselir.

## Manual run

GitHub'da:

```text
Actions → TouristNetTR Hotel Lead Runner → Run workflow
```

Input'lar:

- `target_count`: default 145
- `max_prospects`: default 1000
- `max_pages_per_site`: default 8

## Brave Search opsiyonu

GitHub repo settings içinde secret olarak eklenebilir:

```text
BRAVE_SEARCH_API_KEY
```

Bu eklenirse script `seeds/city_queries.csv` sorgularından aday domain toplamaya çalışır. Secret yoksa sistem seed-only çalışır.

## Sert kurallar

- Tahmini email yok.
- `info@domain`, `sales@domain`, `reservation@domain` ancak kaynakta birebir varsa kabul.
- Telefon yoksa A-tier değil.
- Source URL yoksa A-tier değil.
- Confidence < 90 ise A-tier değil.
- Duplicate kayıt yok.
- 145 tamamlanmadıysa production CSV yok.
