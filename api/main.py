from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import circuits, strategy
from modeling import config
from modeling.optimization import pit_loss

PROCESSED_DIR = Path("data/processed")


def create_app(data_dir: Path = PROCESSED_DIR) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.data_dir = data_dir
        app.state.degradation_coefficients = pd.read_csv(data_dir / "degradation_coefficients.csv")
        app.state.hazard_coefficients = pd.read_csv(data_dir / "hazard_coefficients.csv")
        app.state.laps = pd.read_parquet(data_dir / "laps.parquet")
        app.state.schedule = pd.read_parquet(data_dir / "schedule.parquet")
        app.state.pit_loss_table = pit_loss.estimate_pit_loss(app.state.laps, app.state.schedule)

        app.state.known_circuit_ids = set(app.state.schedule["CircuitId"].unique())
        app.state.known_eras = {era["name"] for era in config.REGULATION_ERAS}

        race_lengths = app.state.laps.groupby(["Season", "Round"])["LapNumber"].max()
        merged = race_lengths.reset_index().merge(
            app.state.schedule[["Season", "Round", "CircuitId"]], on=["Season", "Round"]
        )
        latest = merged.sort_values("Season").groupby("CircuitId").last()
        app.state.default_race_lengths = latest["LapNumber"].astype(int).to_dict()

        app.state.strategy_cache = {}
        yield

    app = FastAPI(title="dispatch", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(circuits.router)
    app.include_router(strategy.router)

    return app


app = create_app()
