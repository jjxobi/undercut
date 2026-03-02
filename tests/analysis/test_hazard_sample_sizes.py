import pandas as pd

from modeling.analysis import hazard_sample_sizes as has


def test_count_events_counts_contiguous_hazard_runs():
    status = pd.DataFrame(
        {
            "Season": [2023] * 6,
            "Round": [1] * 6,
            "Time": pd.timedelta_range("0s", periods=6, freq="min"),
            "Status": ["1", "4", "4", "1", "6", "1"],
        }
    )

    events = has.count_events(status)

    row = events[(events.Season == 2023) & (events.Round == 1)].iloc[0]
    assert row["EventCount"] == 2


def test_count_events_handles_multiple_races_independently():
    status = pd.DataFrame(
        {
            "Season": [2023, 2023, 2023, 2023],
            "Round": [1, 1, 2, 2],
            "Time": pd.timedelta_range("0s", periods=4, freq="min"),
            "Status": ["4", "1", "1", "6"],
        }
    )

    events = has.count_events(status)

    assert events[(events.Season == 2023) & (events.Round == 1)]["EventCount"].item() == 1
    assert events[(events.Season == 2023) & (events.Round == 2)]["EventCount"].item() == 1


def test_sample_sizes_by_circuit_flags_credible_threshold():
    events = pd.DataFrame(
        {
            "Season": [2018, 2019, 2020, 2021],
            "Round": [1, 1, 1, 1],
            "EventCount": [1, 1, 2, 2],
        }
    )
    schedule = pd.DataFrame(
        {
            "Season": [2018, 2019, 2020, 2021],
            "Round": [1, 1, 1, 1],
            "CircuitId": ["monaco"] * 4,
        }
    )

    summary = has.sample_sizes_by_circuit(events, schedule)

    rows = summary[summary.CircuitId == "monaco"]
    assert len(rows) == 1
    row = rows.iloc[0]
    assert row["RaceCount"] == 4
    assert row["TotalEvents"] == 6
    assert row["CredibleForIndividualModel"]
    assert row["RegulationEra"] == "2018-2021 aero"


def test_sample_sizes_by_circuit_flags_low_sample_as_not_credible():
    events = pd.DataFrame({"Season": [2023], "Round": [1], "EventCount": [1]})
    schedule = pd.DataFrame({"Season": [2023], "Round": [1], "CircuitId": ["zandvoort"]})

    summary = has.sample_sizes_by_circuit(events, schedule)

    row = summary[summary.CircuitId == "zandvoort"].iloc[0]
    assert row["RaceCount"] == 1
    assert not row["CredibleForIndividualModel"]


def test_sample_sizes_by_circuit_splits_circuit_spanning_two_eras():
    events = pd.DataFrame(
        {
            "Season": [2021, 2022],
            "Round": [1, 1],
            "EventCount": [1, 3],
        }
    )
    schedule = pd.DataFrame(
        {
            "Season": [2018, 2019, 2020, 2021, 2022, 2023],
            "Round": [1, 1, 1, 1, 1, 1],
            "CircuitId": ["spa"] * 6,
        }
    )

    summary = has.sample_sizes_by_circuit(events, schedule)

    rows = summary[summary.CircuitId == "spa"].sort_values("RegulationEra")
    assert len(rows) == 2

    aero = rows[rows.RegulationEra == "2018-2021 aero"].iloc[0]
    assert aero["RaceCount"] == 4
    assert aero["TotalEvents"] == 1
    assert not aero["CredibleForIndividualModel"]

    ground_effect = rows[rows.RegulationEra == "2022-2025 ground-effect"].iloc[0]
    assert ground_effect["RaceCount"] == 2
    assert ground_effect["TotalEvents"] == 3
    assert not ground_effect["CredibleForIndividualModel"]


def test_sample_sizes_by_circuit_includes_circuits_with_zero_hazard_events():
    events = pd.DataFrame({"Season": [], "Round": [], "EventCount": []})
    schedule = pd.DataFrame(
        {
            "Season": [2023, 2024],
            "Round": [1, 1],
            "CircuitId": ["suzuka"] * 2,
        }
    )

    summary = has.sample_sizes_by_circuit(events, schedule)

    row = summary[summary.CircuitId == "suzuka"].iloc[0]
    assert row["RaceCount"] == 2
    assert row["TotalEvents"] == 0
    assert not row["CredibleForIndividualModel"]
