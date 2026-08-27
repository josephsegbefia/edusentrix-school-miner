from schoolminer.cleaning.geography import resolve_canonical_region


def test_resolve_canonical_region_uses_unambiguous_region() -> None:
    region, status, basis = resolve_canonical_region(
        "Greater Accra Region",
        "Accra Metro",
    )

    assert region == "Greater Accra"
    assert status == "NORMALIZED"

    assert basis == "Greater Accra Region"


def test_bono_source_can_resolve_to_ahafo() -> None:
    region, status, basis = resolve_canonical_region(
        "Bono",
        "Asunafo North",
    )

    assert region == "Ahafo"

    assert status == "RESOLVED_FROM_DISTRICT"

    assert basis == "Asunafo North"


def test_bono_source_can_resolve_to_bono() -> None:
    region, status, basis = resolve_canonical_region(
        "Bono",
        "Sunyani Municipal",
    )

    assert region == "Bono"

    assert status == "RESOLVED_FROM_DISTRICT"

    assert basis == "Sunyani Municipal"


def test_bono_source_can_resolve_to_bono_east() -> None:
    region, status, basis = resolve_canonical_region(
        "Bono",
        "Pru District",
    )

    assert region == "Bono East"

    assert status == "RESOLVED_FROM_DISTRICT"

    assert basis == "Pru District"


def test_historical_volta_can_remain_volta() -> None:
    region, status, basis = resolve_canonical_region(
        "Volta Region",
        "Ketu South Municipal",
    )

    assert region == "Volta"

    assert status == "RESOLVED_FROM_DISTRICT"

    assert basis == "Ketu South Municipal"


def test_historical_volta_can_resolve_to_oti() -> None:
    region, status, basis = resolve_canonical_region(
        "Volta Region",
        "Nkwanta South District",
    )

    assert region == "Oti"

    assert status == "RESOLVED_FROM_DISTRICT"

    assert basis == "Nkwanta South District"


def test_historical_adaklu_anyigbe_resolves_region_only() -> None:
    region, status, basis = resolve_canonical_region(
        "Volta Region",
        "Adaklu-Anyigbe",
    )

    assert region == "Volta"

    assert status == "RESOLVED_FROM_DISTRICT"

    assert basis == "Adaklu-Anyigbe"


def test_historical_western_can_remain_western() -> None:
    region, status, basis = resolve_canonical_region(
        "Western Region",
        "Shama District",
    )

    assert region == "Western"

    assert status == "RESOLVED_FROM_DISTRICT"

    assert basis == "Shama District"


def test_historical_western_can_resolve_to_western_north() -> None:
    region, status, basis = resolve_canonical_region(
        "Western Region",
        "Sefwi Wiawso District",
    )

    assert region == "Western North"

    assert status == "RESOLVED_FROM_DISTRICT"

    assert basis == "Sefwi Wiawso District"


def test_historical_northern_tamale_resolves_to_northern() -> None:
    region, status, basis = resolve_canonical_region(
        "Northern Region",
        "Tamale District",
    )

    assert region == "Northern"

    assert status == "RESOLVED_FROM_DISTRICT"

    assert basis == "Tamale District"


def test_unknown_historical_district_requires_review() -> None:
    region, status, basis = resolve_canonical_region(
        "Western Region",
        "Unknown Old District",
    )

    assert region is None

    assert status == "NEEDS_REVIEW"

    assert basis == "Unknown Old District"


def test_conflicting_region_and_district_requires_review() -> None:
    region, status, basis = resolve_canonical_region(
        "Greater Accra Region",
        "Pru District",
    )

    assert region is None

    assert status == "NEEDS_REVIEW"

    assert "conflict" in basis


def test_missing_geography_remains_missing() -> None:
    region, status, basis = resolve_canonical_region(
        None,
        None,
    )

    assert region is None
    assert status == "MISSING"
    assert basis is None


def test_known_district_can_resolve_missing_region() -> None:
    region, status, basis = resolve_canonical_region(
        None,
        "Pru District",
    )

    assert region == "Bono East"

    assert status == "RESOLVED_FROM_DISTRICT"

    assert basis == "Pru District"
