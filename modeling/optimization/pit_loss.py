from __future__ import annotations

import pandas as pd

MIN_SAMPLES_FOR_CIRCUIT_ESTIMATE = 5
SANITY_MIN_SECONDS = 0
SANITY_MAX_SECONDS = 120

RESULT_COLUMNS = ["circuit_id", "n_stops", "pit_loss_seconds"]


def estimate_pit_loss(laps: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    frame = laps.merge(schedule[["Season", "Round", "CircuitId"]], on=["Season", "Round"], how="inner")
    frame = frame.sort_values(["Season", "Round", "Driver", "LapNumber"]).copy()
    frame["LapTimeSeconds"] = frame["LapTime"].dt.total_seconds()
    frame["NextLapTimeSeconds"] = frame.groupby(["Season", "Round", "Driver"])["LapTimeSeconds"].shift(-1)
    frame["NextTrackStatus"] = frame.groupby(["Season", "Round", "Driver"])["TrackStatus"].shift(-1)

    is_green = frame["TrackStatus"] == "1"
    is_next_green = frame["NextTrackStatus"] == "1"
    is_normal = (
        frame["PitInTime"].isna() & frame["PitOutTime"].isna() & frame["LapTimeSeconds"].notna() & is_green
    )
    normal_median = frame.loc[is_normal].groupby("CircuitId")["LapTimeSeconds"].median()

    pit_rows = frame[
        frame["PitInTime"].notna() & frame["NextLapTimeSeconds"].notna() & is_green & is_next_green
    ].copy()
    pit_rows["ImpliedLoss"] = (
        pit_rows["LapTimeSeconds"] + pit_rows["NextLapTimeSeconds"]
        - 2 * pit_rows["CircuitId"].map(normal_median)
    )
    pit_rows = pit_rows.dropna(subset=["ImpliedLoss"])
    pit_rows = pit_rows[
        (pit_rows["ImpliedLoss"] > SANITY_MIN_SECONDS) & (pit_rows["ImpliedLoss"] < SANITY_MAX_SECONDS)
    ]

    population_median = float(pit_rows["ImpliedLoss"].median()) if len(pit_rows) > 0 else float("nan")
    counts = pit_rows.groupby("CircuitId").size()
    circuit_medians = pit_rows.groupby("CircuitId")["ImpliedLoss"].median()

    records = [{"circuit_id": None, "n_stops": len(pit_rows), "pit_loss_seconds": population_median}]
    for circuit_id, value in circuit_medians.items():
        n_stops = int(counts[circuit_id])
        pit_loss_seconds = float(value) if n_stops >= MIN_SAMPLES_FOR_CIRCUIT_ESTIMATE else population_median
        records.append({"circuit_id": circuit_id, "n_stops": n_stops, "pit_loss_seconds": pit_loss_seconds})

    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)
