from price_tracker.adapters.shopify import _selected_option_values, _variant_matches_options


def test_selected_option_values_from_shopify_option_value_query():
    html = """
    <input value="50g" data-option-value-id="4385721680097" checked>
    <input value="100g" data-option-value-id="4385721712865">
    """
    options = _selected_option_values(
        "https://lazika.com.tr/products/el-yapimi-yesil-cay?option_values=4385721712865",
        html,
    )
    assert options == ["100g"]


def test_variant_matches_selected_options():
    variant = {"options": ["100g"], "price": 54400}
    assert _variant_matches_options(variant, ["100g"])
    assert not _variant_matches_options(variant, ["50g"])
