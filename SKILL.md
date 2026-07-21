---
name: multi_site_price_web_tracker
description: Cok farkli e-ticaret sitelerinden urun fiyati cekme, normalize etme, SQLite'a kaydetme ve FastAPI web arayuzunde kategori bazli analizlerle gosterme becerisi.
---

# SKILL.md - Cok Siteli Fiyat Takip Web Uygulamasi

## Ne zaman kullanilir?
Kullanici kategori bazli urun URL listelerinden fiyat cekmek, sonuclari web arayuzunde gormek, kategori secmek, toplu veri cekmek, yeni URL/kategori eklemek ve mean/medyan gibi basit analizleri hesaplamak isterse bu beceriyi kullan.

## Girdi kaynaklari
Desteklenecek ana kaynak:

1. `kategoriler/*.xlsx`
   - Her dosyada tek `URL` kolonu vardir.
   - Kategori adi dosya adindan gelir.
   - `_urun_listesi.xlsx` son eki kaldirilir.

Ek destek:

2. TXT/CSV
   - Her satir URL olabilir.
   - Kategori yoksa `uncategorized` kullan.

3. Web UI
   - Kullanici var olan kategoriye URL ekleyebilir.
   - Kullanici yeni kategori olusturup URL ekleyebilir.
   - UI kayitlari SQLite'a yazar.

## Canli veri kaynagi
SQLite ana kaynaktir. Excel dosyalari seed/import kaynagidir. Web uygulamasi Excel dosyalarini dogrudan guncellemez.

Temel tablolar:

- `categories`
- `urls`
- `price_results`
- `scrape_jobs`

## Web akisi

```text
FastAPI baslar
  ->
SQLite init
  ->
kategoriler/*.xlsx ice aktarilir
  ->
Dashboard kategori ve ozetleri gosterir
  ->
Kullanici tum verileri veya secili kategoriyi ceker
  ->
Background scrape job calisir
  ->
Her URL sonucu aninda SQLite'a yazilir
  ->
UI job progress ve sonuclari gunceller
```

## UI gereksinimleri
- Kategori secme dropdown'i.
- Secili kategorinin sonuclari.
- Tum verileri cekme butonu.
- Secili kategoriyi cekme butonu.
- Job ilerleme gostergesi.
- Tum sonuclar sayfasi.
- Status/domain/kategori filtreleri.
- Yeni URL ekleme formu.
- Yeni kategori olusturma formu.
- Mean, medyan, min, max, count analizleri.

## Fiyat cikarma sirasi
Her URL icin su sira korunur:

1. Domain adapter
2. JSON-LD / schema.org
3. Meta tag / OpenGraph
4. Gomulu JSON/state
5. HTML fiyat elementi
6. Regex fallback
7. Gerekirse Playwright fallback

## Guven skoru

```text
json_ld: 95
meta_tag: 90
domain_adapter: 90-98
embedded_json: 85
html_price_element: 70-80
regex_near_product_context: 60-70
regex_full_text: 40-55
```

Durum belirleme:

- `confidence >= 70`: `success`
- `confidence < 70`: `low_confidence`
- fiyat yoksa: `not_found`
- timeout varsa: `timeout`
- 403/429 varsa: `blocked`

## Fiyat normalizasyonu
Desteklenecek formatlar:

```text
"1.299,90 TL" -> price=1299.90, currency="TRY"
"₺799,99"     -> price=799.99, currency="TRY"
"799 TL"      -> price=799.00, currency="TRY"
"1299.90 TRY" -> price=1299.90, currency="TRY"
```

Fiyat sayilmamasi gerekenler:

```text
500 gr
1000 gram
1 kg
500 ml
1 lt
%70
99.9%
3 taksit
6 ay
urun kodu
```

## Domain adapter onceligi
Mevcut kategori dosyalarinda sik gecen domainlere oncelik ver:

- `peynircibaba.com`
- `fanusorganik.com`
- `migros.com.tr`
- `karadenizciftlik.com`
- `yayukyoresel.com`
- `tarladanmutfaga.com.tr`
- `neslidogal.com`

Shopify, Ticimax, ikas ve ideasoft benzeri platformlar icin genel adapter eklenebilir.

## Raporlama
SQLite disinda su raporlar uretilebilir:

- `prices.csv`
- `failed_urls.csv`
- `needs_review.csv`
- `prices.xlsx`

XLSX en az su sayfalari icermelidir:

- `all_results`
- `success`
- `needs_review`
- `failed`

## Kod uretirken dikkat
- Web UI ve scraping pipeline ayrik tutulmali.
- Background job tarayiciyi bloke etmemeli.
- Her URL sonucu hemen kaydedilmeli.
- Bir URL hatasi tum job'i durdurmamali.
- Testler canli sitelere bagli olmamali.
- UI server-rendered FastAPI/Jinja olabilir; React zorunlu degildir.
