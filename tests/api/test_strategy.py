from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.test_main import _synthetic_data_dir


def _client(tmp_path):
    data_dir = _synthetic_data_dir(tmp_path)
    return TestClient(create_app(data_dir=data_dir))


def test_solve_strategy_returns_a_feasible_plan(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/strategy",
            json={"circuit_id": "bahrain", "era": "2018-2021 aero", "race_length": 20, "n_scenarios": 5, "seed": 1},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("optimal", "feasible")
    assert sum(body["stint_lengths"]) == 20
    assert len(body["pit_laps"]) == len(body["stint_lengths"]) - 1


def test_solve_strategy_rejects_unknown_circuit(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/strategy",
            json={"circuit_id": "not_a_real_circuit", "era": "2018-2021 aero", "race_length": 20},
        )

    assert response.status_code == 404


def test_solve_strategy_rejects_unknown_era(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/strategy",
            json={"circuit_id": "bahrain", "era": "not_a_real_era", "race_length": 20},
        )

    assert response.status_code == 422


def test_solve_strategy_caches_identical_requests(tmp_path):
    data_dir = _synthetic_data_dir(tmp_path)
    app = create_app(data_dir=data_dir)
    payload = {"circuit_id": "bahrain", "era": "2018-2021 aero", "race_length": 20, "n_scenarios": 5, "seed": 3}

    with TestClient(app) as client:
        first = client.post("/strategy", json=payload)
        cache_size_after_first = len(app.state.strategy_cache)
        second = client.post("/strategy", json=payload)
        cache_size_after_second = len(app.state.strategy_cache)

    assert first.json() == second.json()
    assert cache_size_after_first == 1
    assert cache_size_after_second == 1
