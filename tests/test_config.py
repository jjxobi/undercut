import warnings

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


def test_regulation_era_warns_but_keeps_going_past_confirmed_season():
    # a season past LAST_CONFIRMED_SEASON still resolves to the current era
    # (the pipeline shouldn't break on a new season), but it should say so
    # loudly rather than silently assume the rules haven't changed
    with pytest.warns(UserWarning, match="beyond the last confirmed regulation era"):
        era = config.regulation_era(config.LAST_CONFIRMED_SEASON + 1)
    assert era == "2026 active-aero"


def test_regulation_era_confirmed_seasons_dont_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert config.regulation_era(config.LAST_CONFIRMED_SEASON) == "2026 active-aero"


def test_regulation_era_rejects_season_before_first_era():
    with pytest.raises(ValueError):
        config.regulation_era(2010)
