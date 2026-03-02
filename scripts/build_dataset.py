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
                        "Position": int(position) if position.isdigit() else None,
                        "Status": result["status"],
                        "GridPosition": int(result["grid"]),
                    }
                )

            try:
                session = fastf1_source.load_race_session(season, round_number)
            except Exception:  # noqa: BLE001, S112 - one bad session must not abort the run
                continue

            laps = fastf1_source.laps_frame(session, season, round_number)
            laps_parts.append(laps)
            status_parts.append(fastf1_source.track_status_frame(session, season, round_number))
            weather_parts.append(fastf1_source.weather_frame(session, season, round_number))
            stint_parts.append(fastf1_source.stints_frame(laps))
            pit_parts.append(fastf1_source.pit_stops_frame(laps))

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the processed Dispatch dataset from FastF1 + Jolpica-F1"
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
