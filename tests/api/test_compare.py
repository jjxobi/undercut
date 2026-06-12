from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.test_main import _synthetic_data_dir


def _client(tmp_path):
    data_dir = _synthetic_data_dir(tmp_path)
    return TestClient(create_app(data_dir=data_dir))


def test_compare_returns_both_plans_and_cost_distributions(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/strategy/compare",
            json={"circuit_id": "bahrain", "era": "2018-2021 aero", "race_length": 20, "n_scenarios": 5, "seed": 1},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["deterministic"]["status"] in ("optimal", "feasible")
    assert body["stochastic"]["status"] in ("optimal", "feasible")
    assert len(body["deterministic_costs"]) == 5
    assert len(body["stochastic_costs"]) == 5
    assert isinstance(body["gap_seconds"], float)
    assert isinstance(body["gap_is_significant"], bool)


def test_compare_rejects_unknown_circuit(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/strategy/compare",
            json={"circuit_id": "not_a_real_circuit", "era": "2018-2021 aero", "race_length": 20},
        )

    assert response.status_code == 404


def test_compare_rejects_oversized_race_length(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/strategy/compare",
            json={"circuit_id": "bahrain", "era": "2018-2021 aero", "race_length": 500},
        )

    assert response.status_code == 422
