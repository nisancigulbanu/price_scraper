from price_tracker.normalizers import extract_price_candidates, normalize_price


def test_turkish_price_formats_normalize_to_try():
    assert normalize_price("1.299,90 TL").price == 1299.90
    assert normalize_price("₺1.299,90").price == 1299.90
    assert normalize_price("1299.90 TRY").price == 1299.90
    assert normalize_price("1 299,90 TL").price == 1299.90
    assert normalize_price("799 TL").price == 799.00


def test_regex_ignores_weight_volume_percent_and_installments():
    text = "500 gr urun, 1 kg paket, 500 ml sise, %70 kakao, 6 taksit, fiyat 799,90 TL"
    candidates = extract_price_candidates(text)
    assert [candidate.price for candidate in candidates] == [799.90]
