
import pandas as pd

from scripts import refresh


def test_refresh_calls_every_stage_in_order(tmp_path, monkeypatch):
    calls = []

    def fake_build(seasons, refresh=False):
        calls.append(("build", seasons, refresh))
        return {"laps": pd.DataFrame()}

    def fake_write_tables(tables, out_dir):
        calls.append(("write_tables", out_dir))

    def fake_fit_degradation(processed_dir):
        calls.append(("fit_degradation", processed_dir))
        return pd.DataFrame({"a": [1]})

    def fake_fit_hazard(processed_dir):
        calls.append(("fit_hazard", processed_dir))
        return pd.DataFrame({"a": [1]})

    def fake_fit_field_interaction(processed_dir):
        calls.append(("fit_field_interaction", processed_dir))
        return pd.DataFrame({"a": [1]})

    def fake_run_evaluation(processed_dir):
        calls.append(("run_evaluation", processed_dir))
        return pd.DataFrame({"a": [1]})

    monkeypatch.setattr(refresh.build_dataset, "build", fake_build)
    monkeypatch.setattr(refresh.build_dataset, "write_tables", fake_write_tables)
    monkeypatch.setattr(refresh.fit_degradation_model, "run", fake_fit_degradation)
    monkeypatch.setattr(refresh.fit_hazard_model, "run", fake_fit_hazard)
    monkeypatch.setattr(refresh.fit_field_interaction_model, "run", fake_fit_field_interaction)
    monkeypatch.setattr(refresh.run_evaluation, "run", fake_run_evaluation)

    refresh.refresh(processed_dir=tmp_path, seasons=[2024, 2025])

    stages = [call[0] for call in calls]
    assert stages == [
        "build", "write_tables", "fit_degradation", "fit_hazard", "fit_field_interaction", "run_evaluation",
    ]
    assert calls[0][1] == [2024, 2025]
    assert calls[0][2] is True  # bypasses the jolpica cache to pick up new results
    for stage_call in calls[1:]:
        assert stage_call[-1] == tmp_path

    for filename in [
        "degradation_coefficients.csv", "hazard_coefficients.csv",
        "field_interaction_coefficients.csv", "regret_report.csv",
    ]:
        assert (tmp_path / filename).exists()
