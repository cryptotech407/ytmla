from ytmla.verify import iso_to_seconds


def test_iso_durations():
    assert iso_to_seconds("PT18M3S") == 1083
    assert iso_to_seconds("PT1H2M3S") == 3723
    assert iso_to_seconds("PT43S") == 43
    assert iso_to_seconds("PT1H") == 3600
    assert iso_to_seconds("PT19M8S") == 1148


def test_unparseable_is_zero_not_an_exception():
    for bad in ("", None, "garbage", "18:03"):
        assert iso_to_seconds(bad) == 0


def test_the_pair_that_failed_in_production():
    """18:02 track vs 19:08 video -- the real mismatch."""
    assert iso_to_seconds("PT18M2S") == 1082
    assert iso_to_seconds("PT19M8S") == 1148
    assert abs(iso_to_seconds("PT18M2S") - iso_to_seconds("PT19M8S")) == 66
