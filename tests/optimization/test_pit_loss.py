import pandas as pd

from modeling.optimization import pit_loss


def _laps_row(season, round_, driver, lap, lap_time_s, track_status, pit_in=False, pit_out=False):
    return {
        "Season": season,
        "Round": round_,
        "Driver": driver,
        "LapNumber": lap,
        "LapTime": pd.Timedelta(seconds=lap_time_s),
        "TrackStatus": track_status,
        "PitInTime": pd.Timedelta(seconds=1) if pit_in else pd.NaT,
        "PitOutTime": pd.Timedelta(seconds=1) if pit_out else pd.NaT,
    }


def test_estimate_pit_loss_computes_implied_loss_from_in_and_out_lap():
    # normal green-flag laps run 90s; one driver pits on lap 5 (in-lap 92s,
    # out-lap 112s) -- implied loss = (92+112) - 2*90 = 24s
    rows = [_laps_row(2023, 1, "ver", lap, 90.0, "1") for lap in range(1, 5)]
    rows.append(_laps_row(2023, 1, "ver", 5, 92.0, "1", pit_in=True))
    rows.append(_laps_row(2023, 1, "ver", 6, 112.0, "1", pit_out=True))
    rows += [_laps_row(2023, 1, "ver", lap, 90.0, "1") for lap in range(7, 12)]
    laps = pd.DataFrame(rows)
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]})

    result = pit_loss.estimate_pit_loss(laps, schedule)

    bahrain_row = result[result["circuit_id"] == "bahrain"]
    # single circuit-specific sample -- below MIN_SAMPLES_FOR_CIRCUIT_ESTIMATE,
    # so it must fall back to the population value, which is exactly this one
    # implied-loss observation
    assert len(bahrain_row) == 1
    assert bahrain_row.iloc[0]["pit_loss_seconds"] == 24.0
    assert bahrain_row.iloc[0]["n_stops"] == 1


def test_estimate_pit_loss_excludes_non_green_in_or_out_laps():
    # same as above but the out-lap happens under a safety car (status "4") --
    # must be excluded entirely, leaving no pit-stop observations
    rows = [_laps_row(2023, 1, "ver", lap, 90.0, "1") for lap in range(1, 5)]
    rows.append(_laps_row(2023, 1, "ver", 5, 92.0, "1", pit_in=True))
    rows.append(_laps_row(2023, 1, "ver", 6, 130.0, "4", pit_out=True))
    rows += [_laps_row(2023, 1, "ver", lap, 90.0, "1") for lap in range(7, 12)]
    laps = pd.DataFrame(rows)
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]})

    result = pit_loss.estimate_pit_loss(laps, schedule)

    assert (result["circuit_id"] == "bahrain").sum() == 0


def test_estimate_pit_loss_produces_population_row():
    rows = [_laps_row(2023, 1, "ver", lap, 90.0, "1") for lap in range(1, 5)]
    rows.append(_laps_row(2023, 1, "ver", 5, 92.0, "1", pit_in=True))
    rows.append(_laps_row(2023, 1, "ver", 6, 112.0, "1", pit_out=True))
    rows += [_laps_row(2023, 1, "ver", lap, 90.0, "1") for lap in range(7, 12)]
    laps = pd.DataFrame(rows)
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["bahrain"]})

    result = pit_loss.estimate_pit_loss(laps, schedule)

    assert (result["circuit_id"].isna()).sum() == 1
