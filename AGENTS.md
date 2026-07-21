# AGENTS.md - Cok Siteli Urun Fiyat Takip Web Uygulamasi

## Amac
Bu proje, `kategoriler/` klasorundeki kategori bazli Excel dosyalarindan urun URL'lerini ice aktarir, urun sayfalarindan fiyat bilgisini ceker, fiyatlari normalize eder, guven skoru ve hata bilgisiyle SQLite veritabanina kaydeder ve sonuclari yerel bir web arayuzunde gosterir.

Mevcut veri seti 37 adet `.xlsx` dosyasindan olusur. Her dosya tek `URL` kolonu tasir. Kategori adi dosya adindan turetilir: `_urun_listesi.xlsx` son eki kaldirilir.

## Uygulama modeli
- Python tabanli gelistir.
- Yerel web paneli FastAPI + Jinja2 ile calisir.
- SQLite uygulamanin canli veri kaynagidir.
- `kategoriler/*.xlsx` dosyalari seed/import kaynagidir; web UI yeni kayitlari SQLite'a yazar.
- CSV/XLSX raporlama korunur; CSV icin standart kutuphane, XLSX icin `openpyxl` kullanilir.

## Temel akış
1. `kategoriler/` klasorundeki `.xlsx` dosyalarini oku.
2. Dosya adindan kategori, `URL` kolonundan urun URL'leri uret.
3. URL'leri normalize et ve duplicate kayitlari engelle.
4. URL ve kategori kayitlarini SQLite'a aktar.
5. Web UI'da kategori secimi, sonuc listesi ve toplu cekim aksiyonlari sun.
6. Toplu veya kategori bazli scrape istegini background job olarak calistir.
7. Her URL icin once statik HTTP istegi dene.
8. HTML icinden sirayla fiyat cikar:
   - domain adapter
   - JSON-LD / schema.org `Product` / `Offer`
   - meta tag / OpenGraph fiyat alanlari
   - gomulu JSON/state verileri
   - fiyat class/id alanlari
   - kontrollu regex
9. Gerekirse Playwright fallback kullan.
10. Sonucu URL islenir islenmez SQLite'a kaydet.
11. UI'da kategoriye gore filtrelenmis sonuclar, tum sonuclar ve basit istatistikler goster.

## Web arayuzu
Zorunlu ekranlar:

- Dashboard:
  - kategori dropdown
  - secili kategori sonuc listesi
  - `Tum Verileri Cek` butonu
  - secili kategori icin scrape butonu
  - son job ilerleme bilgisi
  - mean, medyan, min, max, fiyat sayisi

- Sonuclar:
  - kategori, domain ve status filtreleri
  - fiyat, para birimi, guven, yontem, hata ve fetched_at alanlari

- URL Ekle:
  - var olan kategoriye URL ekleme
  - yeni kategori olusturup URL ekleme
  - cok satirli URL girisi
  - invalid URL ve duplicate kontrolu

## Veri modeli
Her fiyat sonucu su alanlari tasimalidir:

```python
class PriceResult:
    source_file: str
    category: str
    url: str
    domain: str
    product_name: str | None
    price: float | None
    currency: str | None
    raw_price: str | None
    method: str
    confidence: int
    status: str
    error: str | None
    fetched_at: str
    http_status: int | None
    final_url: str | None
```

`status` degerleri:

- `success`
- `low_confidence`
- `not_found`
- `blocked`
- `timeout`
- `invalid_url`
- `error`

## Guven skoru
- JSON-LD `offers.price`: 95
- Meta tag urun fiyati: 90
- Bilinen domain adapter sonucu: 90-98
- Gomulu JSON/state sonucu: 85
- HTML class/id fiyat alani: 70-80
- Regex ile urun baglaminda bulunan fiyat: 55-70
- Sayfa genel metninden ilk fiyat: 40-55

Guven skoru 70 altindaysa sonuc `low_confidence` olarak isaretlenmelidir.

## Fiyat normalizasyonu
Turkiye fiyat formatlarini destekle:

- `1.299,90 TL` -> `1299.90`, `TRY`
- `₺1.299,90` -> `1299.90`, `TRY`
- `1299.90 TRY` -> `1299.90`, `TRY`
- `1 299,90 TL` -> `1299.90`, `TRY`
- `799 TL` -> `799.00`, `TRY`

Sunlari fiyat sayma:

- gramaj: `500 gr`, `1000 g`, `1 kg`
- hacim: `500 ml`, `1 lt`
- yuzde: `%70`, `99.9%`
- taksit: `3 taksit`, `6 taksit`
- urun kodu, barkod, kampanya ID'si

## Domain adapter onceligi
Genel pipeline once yazilmali, sonra sik gecen domainler icin adapter eklenmelidir.

Oncelikli domainler:

- `peynircibaba.com`
- `fanusorganik.com`
- `migros.com.tr`
- `karadenizciftlik.com`
- `yayukyoresel.com`
- `tarladanmutfaga.com.tr`
- `neslidogal.com`
- Shopify, Ticimax, ikas, ideasoft benzeri platformlar

Adapter arayuzu:

```python
class BaseAdapter:
    def matches(self, url: str, domain: str) -> bool: ...
    def extract(self, html: str, url: str) -> ExtractedPrice | None: ...
```

Adapter basarisiz olursa genel pipeline devam etmelidir.

## Fetching kurallari
- Varsayilan olarak statik HTTP ile basla.
- `User-Agent` ve `Accept-Language: tr-TR,tr;q=0.9,en;q=0.8` kullan.
- Timeout 15-30 saniye araliginda olsun.
- Ayni domain icin rate limit uygula.
- Playwright yalnizca statik yontemler basarisiz oldugunda veya sayfa JS ile fiyat yukluyor gibi gorundugunde calissin.
- Bot koruma asmaya yonelik zararli veya izinsiz yontem kullanma.

## Ciktilar
Ana web kaynagi SQLite'tir. Raporlama icin su dosyalar uretilebilir:

- `data/output/prices.xlsx`
- `data/output/prices.csv`
- `data/output/failed_urls.csv`
- `data/output/needs_review.csv`

XLSX sayfalari:

- `all_results`
- `success`
- `needs_review`
- `failed`

## CLI hedefleri

```bash
python -m price_tracker.main --serve
python -m price_tracker.main --import-categories
python -m price_tracker.main --input kategoriler --limit 20 --debug
python -m price_tracker.main --input kategoriler --domain migros.com.tr
python -m price_tracker.main --input kategoriler --output data/output/prices.xlsx
```

## Test yaklasimi
Testlerde canli web'e bagimli olma. Fixture HTML ve gecici SQLite veritabani kullan.

Mutlaka test et:

- kategori `.xlsx` dosyalarindan URL okuma
- dosya adindan kategori adi uretme
- yeni URL eklemede duplicate kontrolu
- Turkce fiyat normalizasyonu
- JSON-LD fiyat cikarma
- meta tag fiyat cikarma
- regex'in gramaj/hacim/yuzde/taksiti fiyat sanmamasi
- mean, medyan, min, max analizleri
- hata durumunda job'in durmadan devam etmesi

## Kodlama standartlari
- Her fonksiyon tek is yapsin.
- Fiyat cikarma yontemleri bagimsiz moduller olsun.
- Hatalari yutma; `error` alanina yaz.
- URL islenir islenmez sonucu diske/veritabanina yaz.
- Loglar kullaniciya okunabilir olmali.
- Kodda API key veya gizli bilgi bulunmamali.
