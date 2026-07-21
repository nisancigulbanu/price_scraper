from price_tracker.adapters.default import get_adapter
from price_tracker.adapters.default import (
    GumushanePestilAdapter,
    PestilMarketimAdapter,
    WooCommerceVariationAdapter,
)


def test_fanus_is_not_handled_by_keyword_domain_adapter():
    adapter = get_adapter("https://fanusorganik.com/fanus-cicek-bali-850g", "fanusorganik.com")
    assert adapter is None


def test_woocommerce_variation_adapter_selects_category_quantity():
    html = """
    <h1>SADE KOME GUMUSHANE</h1>
    <form data-product_variations="[
      {&quot;attributes&quot;:{&quot;attribute_gramaj&quot;:&quot;500gr&quot;},&quot;display_price&quot;:275},
      {&quot;attributes&quot;:{&quot;attribute_gramaj&quot;:&quot;1000gr&quot;},&quot;display_price&quot;:500}
    ]"></form>
    """
    result = WooCommerceVariationAdapter().extract(
        html,
        "https://ozerciftlik.com/products/kome/",
        category="1000_gr_cevizli_kome",
    )
    assert result is not None
    assert result.price == 500
    assert result.method == "woocommerce_variant"


def test_gumushane_pestil_adapter_uses_visible_product_price_verified_by_microdata():
    html = """
    <title>Standart Klasik Kome - 780,00 TL</title>
    <div class="product-price-container">
      <div class="product-price">
        <div class="product-price-old">780,00 TL</div>
      </div>
    </div>
    <div class="showcase-price-new">790,00 TL</div>
    <meta itemprop="priceCurrency" content="TRY" />
    <meta itemprop="price" content="780.00" />
    """
    result = GumushanePestilAdapter().extract(
        html,
        "https://www.gumushanepestil.com/urun/standart-klasik-kome-cevizli-sucuk",
    )
    assert result is not None
    assert result.price == 780
    assert result.method == "verified_product_price"


def test_gumushane_pestil_adapter_marks_microdata_only_price_unverified():
    html = """
    <title>Standart Klasik Kome - 780,00 TL</title>
    <div class="showcase-price-new">790,00 TL</div>
    <meta itemprop="priceCurrency" content="TRY" />
    <meta itemprop="price" content="780.00" />
    """
    result = GumushanePestilAdapter().extract(
        html,
        "https://www.gumushanepestil.com/urun/standart-klasik-kome-cevizli-sucuk",
    )
    assert result is not None
    assert result.price == 780
    assert result.method == "microdata_price_unverified"
    assert result.confidence < 70


def test_pestilmarketim_adapter_prefers_main_product_price():
    html = """
    <div class="product-price"><span class="text-accent">₺ 315,00</span></div>
    <span class="h2 font-weight-bold text-accent mr-1">₺ 540,00</span>
    <script>var paket_fiyati = '540'; var paket_fiyati_on = '540,00';</script>
    """
    result = PestilMarketimAdapter().extract(
        html,
        "https://www.pestilmarketim.com/urun/cevizli-kome-1000-gr/204",
    )
    assert result is not None
    assert result.price == 540
    assert result.method == "main_product_price"
