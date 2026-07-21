from price_tracker.adapters.ikas import IkasVariantAdapter


def test_ikas_variant_adapter_selects_price_by_query_quantity():
    html = """
    {"prices":[{"sellPrice":361}],"variantValues":[{"name":"500 g"}]}
    {"prices":[{"sellPrice":722}],"variantValues":[{"name":"1000 g"}]}
    """
    result = IkasVariantAdapter().extract(html, "https://dogapestil.com/kome?Gram=1000-g")
    assert result is not None
    assert result.price == 722
    assert result.method == "ikas_variant"
    assert result.product_name == "1000 g"


def test_ikas_variant_adapter_prefers_main_product_jsonld_offers():
    html = """
    <script type="application/ld+json">
    {"@type":"Product","name":"Köme","offers":[
      {"url":"https://dogapestil.com/kome?vid=variant-500","priceCurrency":"TRY","price":"361.00"},
      {"url":"https://dogapestil.com/kome?vid=variant-1000","priceCurrency":"TRY","price":"722.00"}
    ]}
    </script>
    {"id":"variant-500","variantValues":[{"name":"500 g"}]}
    {"id":"variant-1000","variantValues":[{"name":"1000 g"}]}
    {"prices":[{"sellPrice":843}],"variantValues":[{"name":"1000 g"}],"productId":"other"}
    """
    result = IkasVariantAdapter().extract(html, "https://dogapestil.com/kome?Gram=1000-g")
    assert result is not None
    assert result.price == 722
    assert result.method == "ikas_jsonld_variant"


def test_ikas_variant_adapter_matches_vid_before_offer_order():
    html = """
    <script type="application/ld+json">
    {"@type":"Product","name":"Fındık","offers":[
      {"url":"https://x.test/p?vid=variant-250","priceCurrency":"TRY","price":"709.50"},
      {"url":"https://x.test/p?vid=variant-500","priceCurrency":"TRY","price":"742.50"},
      {"url":"https://x.test/p?vid=variant-1000","priceCurrency":"TRY","price":"1485.00"}
    ]}
    </script>
    {"id":"variant-250","variantValues":[{"name":"250 g"}]}
    {"id":"variant-500","variantValues":[{"name":"500 g"}]}
    {"id":"variant-1000","variantValues":[{"name":"1 kg"}]}
    """
    result = IkasVariantAdapter().extract(html, "https://x.test/p?Gramaj=1-kg")
    assert result is not None
    assert result.price == 1485
