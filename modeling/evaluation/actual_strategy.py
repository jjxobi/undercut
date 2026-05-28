from __future__ import annotations

import pandas as pd

from modeling.optimization import strategy

RESULT_COLUMNS = ["season", "round", "driver", "compounds", "stint_lengths"]


def extract_actual_strategies(
    stints: pd.DataFrame,
    results: pd.DataFrame,
    race_lengths: pd.Series,
    candidate_sequences: list[list[str]] = strategy.CANDIDATE_COMPOUND_SEQUENCES,
) -> pd.DataFrame:
    finished = results[results["Status"].eq("Finished") | results["Status"].str.contains("Lap", na=False)]
    finished_keys = set(zip(finished["Season"], finished["Round"], finished["Code"]))

    records = []
    for (season, round_number, driver), group in stints.groupby(["Season", "Round", "Driver"]):
        if (season, round_number, driver) not in finished_keys:
            continue
        if (season, round_number) not in race_lengths.index:
            continue

        ordered = group.sort_values("Stint")
        compounds = ordered["Compound"].tolist()
        if compounds not in candidate_sequences:
            continue

        stint_lengths = [int(length) for length in ordered["StintLength"].tolist()]
        if sum(stint_lengths) != int(race_lengths.loc[(season, round_number)]):
            continue

        records.append(
            {
                "season": season,
                "round": round_number,
                "driver": driver,
                "compounds": compounds,
                "stint_lengths": stint_lengths,
            }
        )

    return pd.DataFrame.from_records(records, columns=RESULT_COLUMNS)
