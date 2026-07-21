from price_tracker.quantity import extract_quantity, unit_price_per_kg


def test_extract_quantity_prefers_product_name():
    result = extract_quantity(
        product_name="Organik Cicek Bali 850 gr",
        url="https://example.com/cicek-bali-1-kg",
        category="çiçek_bali",
    )
    assert result is not None
    assert result.grams == 850
    assert result.source == "product_name"
    assert result.confidence == 90


def test_query_quantity_overrides_product_name_and_category():
    result = extract_quantity(
        product_name="Kome 1000 gr",
        url="https://dogapestil.com/kome?Gram=500-g",
        category="1000_gr_cevizli_kome",
    )
    assert result is not None
    assert result.grams == 500
    assert result.source == "url_query"
    assert result.confidence == 98


def test_query_quantity_prefers_selected_value_over_option_key():
    result = extract_quantity(
        product_name="Cevizli Kome",
        url="https://fanusorganik.com/cevizli-kome-1000g?500Gr=1-Kg",
        category="1000_gr_cevizli_kome",
    )
    assert result is not None
    assert result.grams == 1000
    assert result.source == "url_query"


def test_extract_quantity_from_url_and_category():
    from_url = extract_quantity(
        product_name=None,
        url="https://example.com/yayla-cicek-bali-1-kg",
        category="çiçek_bali",
    )
    assert from_url is not None
    assert from_url.grams == 1000
    assert from_url.source == "url"

    from_category = extract_quantity(
        product_name=None,
        url="https://example.com/product",
        category="1000_gr_cevizli_kome",
    )
    assert from_category is not None
    assert from_category.grams == 1000
    assert from_category.source == "category"


def test_unit_price_per_kg():
    assert unit_price_per_kg(850, 850) == 1000
    assert unit_price_per_kg(500, 1000) == 500


def test_turkish_thousands_separator_in_quantity():
    result = extract_quantity(
        product_name="Yayla Cicek Bali 1.050 gr",
        url="https://example.com/product",
        category="çiçek_bali",
    )
    assert result is not None
    assert result.grams == 1050
