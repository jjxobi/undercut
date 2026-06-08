from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.test_main import _synthetic_data_dir


def test_list_circuits_returns_known_circuits_and_eras(tmp_path):
    data_dir = _synthetic_data_dir(tmp_path)
    app = create_app(data_dir=data_dir)

    with TestClient(app) as client:
        response = client.get("/circuits")

    assert response.status_code == 200
    body = response.json()
    assert body["circuits"] == [{"circuit_id": "bahrain", "default_race_length": 20}]
    assert "2018-2021 aero" in body["eras"]
    assert "2022-2025 ground-effect" in body["eras"]
