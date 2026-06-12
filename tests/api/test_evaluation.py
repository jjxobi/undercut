import pandas as pd
from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.test_main import _synthetic_data_dir


def test_evaluation_summary_returns_headline_numbers(tmp_path):
    data_dir = _synthetic_data_dir(tmp_path)
    pd.DataFrame(
        [
            {"actual_regret_seconds": 10.0, "policy_regret_seconds": 2.0},
            {"actual_regret_seconds": 20.0, "policy_regret_seconds": 4.0},
        ]
    ).to_csv(data_dir / "regret_report.csv", index=False)
    app = create_app(data_dir=data_dir)

    with TestClient(app) as client:
        response = client.get("/evaluation/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["driver_races"] == 2
    assert body["mean_actual_regret_seconds"] == 15.0
    assert body["mean_policy_regret_seconds"] == 3.0
    assert body["captured_fraction"] == 0.8
    assert isinstance(body["mean_regret_positions_per_race"], float)


def test_evaluation_summary_returns_503_when_report_missing(tmp_path):
    data_dir = _synthetic_data_dir(tmp_path)
    app = create_app(data_dir=data_dir)

    with TestClient(app) as client:
        response = client.get("/evaluation/summary")

    assert response.status_code == 503
