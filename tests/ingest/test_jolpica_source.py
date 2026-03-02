import json

from modeling.ingest import jolpica_source


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


SCHEDULE_PAYLOAD = {
    "MRData": {
        "RaceTable": {
            "Races": [
                {
                    "round": "1",
                    "raceName": "Bahrain Grand Prix",
                    "date": "2023-03-05",
                    "Circuit": {"circuitId": "bahrain"},
                }
            ]
        }
    }
}

RESULTS_PAYLOAD = {
    "MRData": {
        "RaceTable": {
            "Races": [
                {
                    "Results": [
                        {
                            "position": "1",
                            "positionText": "1",
                            "grid": "2",
                            "status": "Finished",
                            "Driver": {"driverId": "max_verstappen"},
                        }
                    ]
                }
            ]
        }
    }
}


def test_season_schedule_fetches_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(jolpica_source, "CACHE_DIR", tmp_path)
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return _FakeResponse(SCHEDULE_PAYLOAD)

    monkeypatch.setattr(jolpica_source.requests, "get", fake_get)

    races = jolpica_source.season_schedule(2023)

    assert races[0]["raceName"] == "Bahrain Grand Prix"
    assert calls == ["https://api.jolpi.ca/ergast/f1/2023.json"]
    assert (tmp_path / "schedule_2023.json").exists()


def test_season_schedule_uses_cache_without_network_call(tmp_path, monkeypatch):
    monkeypatch.setattr(jolpica_source, "CACHE_DIR", tmp_path)
    (tmp_path / "schedule_2023.json").write_text(json.dumps(SCHEDULE_PAYLOAD))

    def fail_get(*args, **kwargs):
        raise AssertionError("should not hit network when cache exists")

    monkeypatch.setattr(jolpica_source.requests, "get", fail_get)

    races = jolpica_source.season_schedule(2023)

    assert races[0]["raceName"] == "Bahrain Grand Prix"


def test_season_schedule_refresh_bypasses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(jolpica_source, "CACHE_DIR", tmp_path)
    (tmp_path / "schedule_2023.json").write_text(json.dumps(SCHEDULE_PAYLOAD))
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return _FakeResponse(SCHEDULE_PAYLOAD)

    monkeypatch.setattr(jolpica_source.requests, "get", fake_get)

    races = jolpica_source.season_schedule(2023, refresh=True)

    assert races[0]["raceName"] == "Bahrain Grand Prix"
    assert calls == ["https://api.jolpi.ca/ergast/f1/2023.json"]


def test_race_results_refresh_bypasses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(jolpica_source, "CACHE_DIR", tmp_path)
    (tmp_path / "results_2023_1.json").write_text(json.dumps(RESULTS_PAYLOAD))
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return _FakeResponse(RESULTS_PAYLOAD)

    monkeypatch.setattr(jolpica_source.requests, "get", fake_get)

    results = jolpica_source.race_results(2023, 1, refresh=True)

    assert results[0]["Driver"]["driverId"] == "max_verstappen"
    assert calls == ["https://api.jolpi.ca/ergast/f1/2023/1/results.json"]


def test_race_results_returns_results_list(tmp_path, monkeypatch):
    monkeypatch.setattr(jolpica_source, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        jolpica_source.requests, "get", lambda url, timeout: _FakeResponse(RESULTS_PAYLOAD)
    )

    results = jolpica_source.race_results(2023, 1)

    assert results[0]["Driver"]["driverId"] == "max_verstappen"


def test_race_results_returns_empty_list_when_no_races(tmp_path, monkeypatch):
    monkeypatch.setattr(jolpica_source, "CACHE_DIR", tmp_path)
    empty_payload = {"MRData": {"RaceTable": {"Races": []}}}
    monkeypatch.setattr(
        jolpica_source.requests, "get", lambda url, timeout: _FakeResponse(empty_payload)
    )

    results = jolpica_source.race_results(2023, 99)

    assert results == []
