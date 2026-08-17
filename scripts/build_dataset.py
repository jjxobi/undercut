from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modeling import config
from modeling.ingest import fastf1_source, jolpica_source

PROCESSED_DIR = Path("data/processed")


def build(seasons: list[int], refresh: bool = False) -> dict[str, pd.DataFrame]:
    fastf1_source.enable_cache()

    laps_parts, status_parts, weather_parts = [], [], []
    stint_parts, pit_parts, schedule_parts, results_parts = [], [], [], []

    for season in seasons:
        races = jolpica_source.season_schedule(season, refresh=refresh)
        for race in races:
            round_number = int(race["round"])
            schedule_parts.append(
                {
                    "Season": season,
                    "Round": round_number,
                    "RaceName": race["raceName"],
                    "CircuitId": race["Circuit"]["circuitId"],
                    "Date": race["date"],
                }
            )

            for result in jolpica_source.race_results(season, round_number, refresh=refresh):
                position = result["position"]
                results_parts.append(
                    {
                        "Season": season,
                        "Round": round_number,
                        "Driver": result["Driver"]["driverId"],
                        "Code": result["Driver"]["code"],
                        "Position": int(position) if position.isdigit() else None,
                        "Status": result["status"],
                        "GridPosition": int(result["grid"]),
                    }
                )

            try:
                session = fastf1_source.load_race_session(season, round_number)
                laps = fastf1_source.laps_frame(session, season, round_number)
                status = fastf1_source.track_status_frame(session, season, round_number)
                weather = fastf1_source.weather_frame(session, season, round_number)
                stints = fastf1_source.stints_frame(laps)
                pit_stops = fastf1_source.pit_stops_frame(laps)
            except Exception as exc:  # noqa: BLE001 - one bad session must not abort the run
                print(f"skip {season} round {round_number}: {exc}")
                continue

            laps_parts.append(laps)
            status_parts.append(status)
            weather_parts.append(weather)
            stint_parts.append(stints)
            pit_parts.append(pit_stops)

    def _concat(parts: list[pd.DataFrame]) -> pd.DataFrame:
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    return {
        "laps": _concat(laps_parts),
        "track_status": _concat(status_parts),
        "weather": _concat(weather_parts),
        "stints": _concat(stint_parts),
        "pit_stops": _concat(pit_parts),
        "schedule": pd.DataFrame(schedule_parts),
        "results": pd.DataFrame(results_parts),
    }


def write_tables(tables: dict[str, pd.DataFrame], out_dir: Path = PROCESSED_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_parquet(out_dir / f"{name}.parquet", index=False)


def merge_and_write_tables(
    tables: dict[str, pd.DataFrame], seasons: list[int], out_dir: Path = PROCESSED_DIR
) -> None:
    """Replace the given seasons' rows in the on-disk tables, leaving every other season untouched."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, fresh_frame in tables.items():
        existing_path = out_dir / f"{name}.parquet"
        if existing_path.exists():
            existing = pd.read_parquet(existing_path)
            existing = existing[~existing["Season"].isin(seasons)]
            merged = pd.concat([existing, fresh_frame], ignore_index=True)
        else:
            merged = fresh_frame
        merged.to_parquet(existing_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the processed Undercut dataset from FastF1 + Jolpica-F1"
    )
    parser.add_argument("--seasons", type=int, nargs="*", default=config.SEASONS)
    parser.add_argument("--out", type=Path, default=PROCESSED_DIR)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="bypass the Jolpica-F1 cache and re-fetch schedule/results from the network",
    )
    args = parser.parse_args()

    tables = build(args.seasons, refresh=args.refresh)
    write_tables(tables, args.out)


if __name__ == "__main__":
    main()
