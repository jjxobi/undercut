from __future__ import annotations

import numpy as np
import pandas as pd

MIN_DRIVERS_FOR_SIGNATURE = 8
LAP_TIME_THRESHOLD = 1.07
SECTOR_SUM_TOLERANCE_SECONDS = 0.5
MIN_VARIANT_THRESHOLD = 0.05
NULL_DISTANCE_QUANTILE = 0.995

SECTOR_TIME_COLUMNS = ["Sector1Time", "Sector2Time", "Sector3Time"]
SECTOR_FRACTION_COLUMNS = ["Sector1Frac", "Sector2Frac", "Sector3Frac"]


def _representative_laps(laps: pd.DataFrame) -> pd.DataFrame:
    frame = laps.dropna(subset=[*SECTOR_TIME_COLUMNS, "LapTime", "CircuitId"]).copy()
    for column in SECTOR_TIME_COLUMNS:
        frame[f"{column}Seconds"] = frame[column].dt.total_seconds()
    frame["LapTimeSeconds"] = frame["LapTime"].dt.total_seconds()
    frame["SectorSum"] = frame[[f"{c}Seconds" for c in SECTOR_TIME_COLUMNS]].sum(axis=1)

    reconciles = (frame["SectorSum"] - frame["LapTimeSeconds"]).abs() < SECTOR_SUM_TOLERANCE_SECONDS
    frame = frame[reconciles]

    race_best = frame.groupby(["Season", "Round"])["LapTimeSeconds"].transform("min")
    frame = frame[frame["LapTimeSeconds"] <= LAP_TIME_THRESHOLD * race_best]

    for column in SECTOR_TIME_COLUMNS:
        frame[column.replace("Time", "Frac")] = frame[f"{column}Seconds"] / frame["SectorSum"]
    return frame


def compute_race_signatures(laps: pd.DataFrame) -> pd.DataFrame:
    """One centered-log-ratio sector-fraction signature per (Season, Round, CircuitId).

    `laps` must already have `CircuitId` joined (see `features.add_circuit`). Races
    with fewer than MIN_DRIVERS_FOR_SIGNATURE representative drivers are dropped --
    there isn't enough signal to trust a signature for them (e.g. a very wet race).
    """
    frame = _representative_laps(laps)
    per_driver = (
        frame.groupby(["Season", "Round", "CircuitId", "Driver"])[SECTOR_FRACTION_COLUMNS]
        .median()
    )
    driver_counts = per_driver.groupby(level=["Season", "Round", "CircuitId"]).size()
    valid_races = driver_counts[driver_counts >= MIN_DRIVERS_FOR_SIGNATURE].index
    per_driver = per_driver.loc[per_driver.index.droplevel("Driver").isin(valid_races)]

    signature = per_driver.groupby(level=["Season", "Round", "CircuitId"]).median()
    log_signature = np.log(signature)
    return log_signature.sub(log_signature.mean(axis=1), axis=0)


def _null_distance_threshold(signatures: pd.DataFrame) -> float:
    """Self-calibrating threshold: a high quantile of the pooled within-circuit
    same-layout distance distribution. Nearly all within-circuit race pairs are
    same-layout, so this distribution estimates "no change" directly from the
    data and re-calibrates automatically as more seasons arrive.
    """
    distances = []
    for _circuit_id, group in signatures.groupby(level="CircuitId"):
        values = group.values
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                distances.append(float(np.max(np.abs(values[i] - values[j]))))
    if not distances:
        return MIN_VARIANT_THRESHOLD
    return max(MIN_VARIANT_THRESHOLD, float(np.quantile(distances, NULL_DISTANCE_QUANTILE)))


def detect_variants(signatures: pd.DataFrame, threshold: float | None = None) -> pd.Series:
    """Maps each (Season, Round, CircuitId) to a variant label, e.g. "bahrain_v0".

    Online nearest-reference assignment, processed in chronological order per
    circuit: each race joins whichever existing variant's reference signature it's
    closest to, if within `threshold`; otherwise it starts a new variant. This
    correctly handles reverting to an earlier layout (e.g. Bahrain returning to
    its standard layout in 2021 after the one-off 2020 Sakhir race) because every
    race is compared against ALL previously-seen variants at that circuit, not
    just the most recent one.
    """
    if threshold is None:
        threshold = _null_distance_threshold(signatures)

    variant_labels: dict[tuple, str] = {}
    for circuit_id, group in signatures.groupby(level="CircuitId"):
        races = sorted(group.index)
        references: list[tuple[int, np.ndarray]] = []
        for race in races:
            signature = group.loc[race].values
            best_index, best_distance = None, None
            for index, reference in references:
                distance = float(np.max(np.abs(signature - reference)))
                if best_distance is None or distance < best_distance:
                    best_index, best_distance = index, distance
            if best_index is not None and best_distance <= threshold:
                variant_labels[race] = f"{circuit_id}_v{best_index}"
            else:
                new_index = len(references)
                references.append((new_index, signature))
                variant_labels[race] = f"{circuit_id}_v{new_index}"

    return pd.Series(variant_labels, name="Variant")
