from __future__ import annotations

import json
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api import circuits, compare, evaluation, strategy
from api.compare import CompareResponse
from api.strategy import StrategyResponse
from modeling import config
from modeling.optimization import pit_loss
from scripts.warm_cache import OUTPUT_FILENAME as WARM_CACHE_FILENAME
from scripts.warm_cache import parse_cache_key

PROCESSED_DIR = Path("data/processed")


class HealthResponse(BaseModel):
    status: str


def create_app(data_dir: Path = PROCESSED_DIR) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.data_dir = data_dir
        app.state.degradation_coefficients = pd.read_csv(data_dir / "degradation_coefficients.csv")
        app.state.hazard_coefficients = pd.read_csv(data_dir / "hazard_coefficients.csv")
        app.state.laps = pd.read_parquet(data_dir / "laps.parquet")
        app.state.schedule = pd.read_parquet(data_dir / "schedule.parquet")
        app.state.results = pd.read_parquet(data_dir / "results.parquet")
        app.state.pit_loss_table = pit_loss.estimate_pit_loss(app.state.laps, app.state.schedule)

        app.state.known_circuit_ids = set(app.state.schedule["CircuitId"].unique())
        app.state.known_eras = {era["name"] for era in config.REGULATION_ERAS}

        race_lengths = app.state.laps.groupby(["Season", "Round"])["LapNumber"].max()
        merged = race_lengths.reset_index().merge(
            app.state.schedule[["Season", "Round", "CircuitId"]], on=["Season", "Round"]
        )
        latest = merged.sort_values("Season").groupby("CircuitId").last()
        app.state.default_race_lengths = latest["LapNumber"].astype(int).to_dict()

        app.state.strategy_cache = OrderedDict()
        app.state.compare_cache = OrderedDict()

        warm_cache_path = data_dir / WARM_CACHE_FILENAME
        if warm_cache_path.exists():
            warm = json.loads(warm_cache_path.read_text())
            for key, entry in warm.get("strategy", {}).items():
                app.state.strategy_cache[parse_cache_key(key)] = StrategyResponse(**entry)
            for key, entry in warm.get("compare", {}).items():
                app.state.compare_cache[parse_cache_key(key)] = CompareResponse(**entry)

        yield

    app = FastAPI(title="undercut", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    app.include_router(circuits.router)
    app.include_router(strategy.router)
    app.include_router(evaluation.router)
    app.include_router(compare.router)

    return app


app = create_app()
