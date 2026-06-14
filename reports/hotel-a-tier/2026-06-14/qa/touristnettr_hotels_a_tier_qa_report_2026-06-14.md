# Hotel Lead QA Report — 2026-06-14

## Input

- Source CSV: `leads/hotel-a-tier/2026-06-14/touristnettr_hotels_a_tier_2026-06-14.csv`
- Total rows checked: 145
- Clean usable rows: 0
- Review-needed rows: 145

## Flag counts

- city_inferred: 134
- domain_mismatch: 16
- city_missing: 11
- suspicious_phone: 5
- free_email: 4
- confidence_below_100: 4
- duplicate_email: 2
- duplicate_phone: 2
- duplicate_domain_email_phone: 2
- weak_email_domain: 1

## Decision

Use `clean_usable` for first outreach. Do not mail `review_needed` until manually checked or fixed.

## Review examples

| hotel_name | email | phone | website | qa_flags |
|---|---|---|---|---|
| A'la Sofia Hotel | info@alasofiahotel.com | +902125189505 | https://www.alasofiahotel.com/tr | city_inferred |
| Acra Hotel | acra@acrahotel.com | +902124589410 | https://acrahotel.com/ | city_inferred |
| Adamar Hotel Sultanahmet Istanbul | info@adamarhotel.com | +902125111937 | https://adamarhotel.com/ | city_inferred |
| Agora Life Hotel | info@agoralifehotel.com | +902125261181 | https://www.agoralifehotel.com/ | city_inferred |
| Akbıyık Suite Boutique Hotel | info@akbiyiksuite.com | +902125171316 | http://www.akbiyiksuite.com/ | city_inferred |
| Alhambra Residence | info@alhambraaparthotel.com | +902126382721 | https://www.alhambraaparthotel.com/ | city_inferred |
| All Seasons Hotel | reservation@hotelallseasons.com | +902126358383 | https://www.hotelallseasons.com/tr | city_inferred |
| All Seasons Suites | info@allseasonssuites.com | +902125235050 | https://www.allseasonssuites.com/tr | city_inferred |
| Almina inn Hotel | info@alminainnhotel.com | +902125187102 | https://alminainnhotel.com/ | city_inferred |
| Alpek Hotel | info@alpekhotel.com | +902125144582 | https://alpekhotel.com/ | city_inferred |
| Anadolu Hotel | info@anadoluhotel.com | +902125121035 | http://www.anadoluhotel.com/ | city_inferred |
| Antea Hotel Oldcity | info@anteahotel.com | +902126381121 | http://www.anteahotel.com/ | city_inferred |
| Antea Palace Hotel & Spa | info@hotelanteapalace.com | +902124583636 | http://hotelanteapalace.com/ | city_inferred |
| Anthemis Hotel | info@anthemishotel.com | +902125110370 | https://anthemishotel.com/ | city_inferred |
| Antik Hotel Istanbul | info@antikhotel.com | +902126385858 | https://www.antikhotel.com/ | city_inferred |
| Antis Hotel | info@antishotel.com | +902125182021 | http://www.antishotel.com/contact.html | city_inferred |
| Antusa Design Hotel & Spa | info@antusadesignhotel.com | +902125146341 | https://www.antusadesignhotel.com/ | city_inferred |
| Antusa Palace Hotel | info@antusapalacehotel.com | +902125110771 | https://www.antusapalacehotel.com/ | city_inferred |
| Arife Sultan Hotel | info@arifesultanhotel.com | +902125140373 | https://arifesultanhotel.com/ | city_inferred |
| Aristocrat Hotel Sultanahmet | info@aristocrathotel.com | +901843133517 | https://aristocrathotel.com/ | city_inferred;suspicious_phone |
| Arven Hotel | info@arvenhotel.com | +902124580910 | http://www.arvenhotel.com/ | city_inferred |
| Askoç Hotel | info@askochotel.com | +902125118089 | https://askochotel.com | city_inferred |
| Asur | info@hotelasur.com | +905072462397 | https://hotelasur.com/ | city_missing |
| Avicenna Hotel | info@avicennahotel.com | +905055267434 | http://www.avicennahotel.com/ | city_missing |
| Avrasya Port Hotel | info@avrasyaport.com | +902125862636 | https://www.avrasyaport.com/ | city_inferred |
| Ayasultan Hotel Istanbul | info@ayasultanhotel.com | +902125192222 | https://www.ayasultanhotel.com/tr | city_inferred |
| Aybar Hotel | reservation@hotelaybar.com | +902125281161 | http://hotelaybar.com/ | city_inferred |
| BALPETEK HOTEL | info@balpetekhotel.com | +902125208866 | https://www.balpetekhotel.com/ | city_inferred |
| Barin Hotel | info@barinhotel.com | +902125139100 | https://www.barinhotel.com/tr | city_inferred |
| Baron Hotel | info@baronhotel.com | +902125167025 | http://www.baronhotel.com.tr/ | city_inferred;domain_mismatch |
