from __future__ import annotations

from pathlib import Path

import pandas as pd

from modeling import config

SC_VSC_CODES = {"4", "6"}


def count_events(status: pd.DataFrame) -> pd.DataFrame:
    status = status.sort_values(["Season", "Round", "Time"]).reset_index(drop=True)
    status = status.copy()
    status["IsHazard"] = status["Status"].astype(str).isin(SC_VSC_CODES)
    status["GroupKey"] = list(zip(status["Season"], status["Round"]))
    status["Changed"] = (
        status["IsHazard"] != status.groupby("GroupKey")["IsHazard"].shift()
    ).astype(int)
    status["EventId"] = status.groupby("GroupKey")["Changed"].cumsum()

    hazard_rows = status[status["IsHazard"]]
    return (
        hazard_rows.groupby(["Season", "Round", "EventId"])
        .size()
        .reset_index()
        .groupby(["Season", "Round"])
        .size()
        .reset_index(name="EventCount")
    )


def sample_sizes_by_circuit(events: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    merged = events.merge(schedule[["Season", "Round", "CircuitId"]], on=["Season", "Round"], how="left")
    merged["RegulationEra"] = merged["Season"].apply(config.regulation_era)
    summary = (
        merged.groupby("CircuitId")
        .agg(TotalEvents=("EventCount", "sum"), RaceCount=("Round", "count"))
        .reset_index()
        .sort_values("TotalEvents")
    )
    era_by_circuit = merged.sort_values("Season").groupby("CircuitId")["RegulationEra"].last()
    summary["RegulationEra"] = summary["CircuitId"].map(era_by_circuit)
    summary["CredibleForIndividualModel"] = summary["TotalEvents"] >= 5
    return summary


def main(processed_dir: Path = Path("data/processed")) -> pd.DataFrame:
    status = pd.read_parquet(processed_dir / "track_status.parquet")
    schedule = pd.read_parquet(processed_dir / "schedule.parquet")
    events = count_events(status)
    summary = sample_sizes_by_circuit(events, schedule)
    summary.to_csv(processed_dir / "sc_vsc_sample_sizes.csv", index=False)
    return summary


if __name__ == "__main__":
    main()
