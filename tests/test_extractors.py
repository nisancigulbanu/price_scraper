from price_tracker.extractors.jsonld import extract_jsonld
from price_tracker.extractors.meta import extract_meta
from price_tracker.extractors.regex_price import extract_regex_price


def test_jsonld_extracts_offer_price():
    html = """
    <script type="application/ld+json">
    {"@type":"Product","name":"Tereyagi","offers":{"@type":"Offer","price":"249.90","priceCurrency":"TRY"}}
    </script>
    """
    result = extract_jsonld(html)
    assert result is not None
    assert result.price == 249.90
    assert result.method == "json_ld"
    assert result.confidence == 95


def test_meta_extracts_product_price():
    html = """
    <meta property="og:title" content="Bal">
    <meta property="product:price:amount" content="399,90">
    <meta property="product:price:currency" content="TRY">
    """
    result = extract_meta(html)
    assert result is not None
    assert result.price == 399.90
    assert result.method == "meta_tag"


def test_regex_extracts_price_without_treating_gram_as_price():
    result = extract_regex_price("<main>Urun 1000 gr. Sepette fiyat 549,90 TL</main>")
    assert result is not None
    assert result.price == 549.90
