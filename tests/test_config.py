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


def test_regulation_era_open_ended_covers_future_seasons():
    # no era configured beyond 2026 yet -- future seasons fall into the
    # latest open-ended era until someone adds a new row to REGULATION_ERAS
    assert config.regulation_era(2027) == "2026 active-aero"


def test_regulation_era_rejects_season_before_first_era():
    with pytest.raises(ValueError):
        config.regulation_era(2010)
