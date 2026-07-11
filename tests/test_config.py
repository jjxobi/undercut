import pytest

from modeling import config


def test_seasons_covers_2018_through_current_config():
    assert 2018 in config.SEASONS
    assert 2026 in config.SEASONS
    assert config.SEASONS == sorted(config.SEASONS)


def test_regulation_era_known_boundaries():
    assert config.regulation_era(2018) == "2018-2021 aero"
    assert config.regulation_era(2021) == "2018-2021 aero"
    assert config.regulation_era(2022) == "2022-2025 ground-effect"
    assert config.regulation_era(2025) == "2022-2025 ground-effect"
    assert config.regulation_era(2026) == "2026 active-aero"


def test_regulation_era_rejects_unconfirmed_future_season():
    # a season past LAST_CONFIRMED_SEASON must fail loudly instead of silently
    # inheriting the current era -- that call is only safe once a human has
    # checked whether new technical regulations apply
    with pytest.raises(ValueError, match="beyond the last confirmed regulation era"):
        config.regulation_era(config.LAST_CONFIRMED_SEASON + 1)


def test_regulation_era_rejects_season_before_first_era():
    with pytest.raises(ValueError):
        config.regulation_era(2010)
