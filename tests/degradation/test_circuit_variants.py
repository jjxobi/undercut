import numpy as np
import pandas as pd
import pytest

from modeling.degradation import circuit_variants


def _signature_frame(rows: dict) -> pd.DataFrame:
    index = pd.MultiIndex.from_tuples(rows.keys(), names=["Season", "Round", "CircuitId"])
    return pd.DataFrame(list(rows.values()), index=index, columns=circuit_variants.SECTOR_FRACTION_COLUMNS)


def _clr(fracs: tuple[float, float, float]) -> np.ndarray:
    """Centered-log-ratio of a raw (not necessarily normalized) 3-vector, matching
    what compute_race_signatures produces from real sector fractions."""
    log_fracs = np.log(np.array(fracs, dtype=float))
    return log_fracs - log_fracs.mean()


def _laps_for_race(
    season: int,
    round_number: int,
    circuit_id: str,
    n_drivers: int,
    sector_fracs: tuple[float, float, float],
    rng: np.random.Generator,
    n_laps: int = 15,
    lap_time_base: float = 90.0,
    noise_sd: float = 0.3,
) -> list[dict]:
    rows = []
    for driver_index in range(n_drivers):
        driver = f"D{driver_index}"
        for _ in range(n_laps):
            total = lap_time_base + rng.normal(0, noise_sd)
            s1 = total * sector_fracs[0] + rng.normal(0, 0.03)
            s2 = total * sector_fracs[1] + rng.normal(0, 0.03)
            s3 = total - s1 - s2
            rows.append(
                {
                    "Season": season,
                    "Round": round_number,
                    "CircuitId": circuit_id,
                    "Driver": driver,
                    "Sector1Time": pd.Timedelta(seconds=s1),
                    "Sector2Time": pd.Timedelta(seconds=s2),
                    "Sector3Time": pd.Timedelta(seconds=s3),
                    "LapTime": pd.Timedelta(seconds=s1 + s2 + s3),
                }
            )
    return rows


def test_compute_race_signatures_builds_centered_log_ratio_per_race():
    rng = np.random.default_rng(0)
    laps = pd.DataFrame(_laps_for_race(2023, 1, "bahrain", 10, (0.30, 0.35, 0.35), rng))

    signatures = circuit_variants.compute_race_signatures(laps)

    assert (2023, 1, "bahrain") in signatures.index
    row = signatures.loc[(2023, 1, "bahrain")]
    # a centered-log-ratio transform sums to (approximately) zero by construction
    assert row.sum() == pytest.approx(0.0, abs=1e-6)


def test_compute_race_signatures_drops_race_with_too_few_representative_drivers():
    rng = np.random.default_rng(1)
    # 5 drivers -- below MIN_DRIVERS_FOR_SIGNATURE (8), e.g. a very wet race with
    # few representative (non-outlier) laps
    laps = pd.DataFrame(_laps_for_race(2023, 1, "spa", 5, (0.30, 0.35, 0.35), rng))

    signatures = circuit_variants.compute_race_signatures(laps)

    assert (2023, 1, "spa") not in signatures.index
    assert len(signatures) == 0


def test_detect_variants_separates_short_layout_race_from_normal_races():
    # 3 near-identical "normal layout" signatures plus 1 clearly different
    # "short layout" signature (matching the real bahrain 2020 Sakhir case in
    # shape, not scale). An explicit threshold is used here so this test
    # exercises the online nearest-reference assignment logic in isolation,
    # independent of the self-calibrated threshold's own numeric behavior
    # (covered separately below).
    normal = _clr((0.30, 0.35, 0.35))
    short_layout = _clr((0.45, 0.30, 0.25))
    rows = {
        (2019, 1, "bahrain"): normal + np.array([0.001, -0.0005, -0.0005]),
        (2020, 2, "bahrain"): normal + np.array([-0.001, 0.0005, 0.0005]),
        (2020, 16, "bahrain"): short_layout,
        (2021, 3, "bahrain"): normal,
    }
    signatures = _signature_frame(rows)

    variants = circuit_variants.detect_variants(signatures, threshold=0.05)

    normal_variant = variants[[(2019, 1, "bahrain"), (2020, 2, "bahrain"), (2021, 3, "bahrain")]]
    assert normal_variant.nunique() == 1
    assert variants[(2020, 16, "bahrain")] != normal_variant.iloc[0]


def test_detect_variants_keeps_single_variant_when_no_layout_change():
    normal = _clr((0.28, 0.40, 0.32))
    rows = {
        (2019, 1, "monza"): normal + np.array([0.001, -0.0005, -0.0005]),
        (2020, 2, "monza"): normal + np.array([-0.0008, 0.0004, 0.0004]),
        (2021, 3, "monza"): normal,
    }
    signatures = _signature_frame(rows)

    variants = circuit_variants.detect_variants(signatures, threshold=0.05)

    assert variants.nunique() == 1


def test_detect_variants_rejoins_earlier_variant_after_reversion():
    # Reproduces the real yas_marina case: standard layout (A), a one-off
    # reprofile (B), then back to standard (A) again. Every race must be
    # compared against ALL previously-seen variants, not just the most
    # recent one, or the second "A" race would incorrectly start a new
    # variant C instead of rejoining the original A.
    variant_a = _clr((0.30, 0.35, 0.35))
    variant_b = _clr((0.20, 0.45, 0.35))
    rows = {
        (2018, 1, "yas_marina"): variant_a + np.array([0.0008, -0.0004, -0.0004]),
        (2019, 2, "yas_marina"): variant_a + np.array([-0.0008, 0.0004, 0.0004]),
        (2020, 3, "yas_marina"): variant_b,
        (2021, 4, "yas_marina"): variant_a,
    }
    signatures = _signature_frame(rows)

    variants = circuit_variants.detect_variants(signatures, threshold=0.05)

    assert variants[(2018, 1, "yas_marina")] == variants[(2019, 2, "yas_marina")]
    assert variants[(2018, 1, "yas_marina")] == variants[(2021, 4, "yas_marina")]
    assert variants[(2020, 3, "yas_marina")] != variants[(2018, 1, "yas_marina")]


def test_detect_variants_self_calibrates_threshold_from_null_distribution():
    # Exercises the default (threshold=None) self-calibration path, which
    # pools pairwise same-circuit distances across ALL circuits to estimate
    # "no change." That pool needs to be dominated by genuine same-layout
    # pairs to work -- realistic on the real multi-season, multi-circuit
    # dataset (where layout changes are rare events among many circuits),
    # so this test uses a comparably-shaped background: many circuits with
    # only same-layout races, plus one circuit with a real layout change.
    rng = np.random.default_rng(5)
    rows = {}
    for i in range(20):
        base = rng.normal(0, 0.02, size=3)
        base -= base.mean()
        for r in range(4):
            noise = rng.normal(0, 0.01, size=3)
            vector = base + noise
            rows[(2020, i * 10 + r, f"circuit_{i}")] = vector - vector.mean()

    target_base = rng.normal(0, 0.02, size=3)
    target_base -= target_base.mean()
    for r in range(3):
        noise = rng.normal(0, 0.01, size=3)
        vector = target_base + noise
        rows[(2020, 900 + r, "bahrain")] = vector - vector.mean()
    outlier = target_base + np.array([0.25, -0.1, -0.15])
    rows[(2020, 916, "bahrain")] = outlier - outlier.mean()

    signatures = _signature_frame(rows)

    variants = circuit_variants.detect_variants(signatures)

    bahrain_variants = variants[[k for k in rows if k[2] == "bahrain"]]
    normal_races = [(2020, 900, "bahrain"), (2020, 901, "bahrain"), (2020, 902, "bahrain")]
    assert bahrain_variants[normal_races].nunique() == 1
    assert variants[(2020, 916, "bahrain")] not in set(bahrain_variants[normal_races])
    for i in range(20):
        circuit_keys = [k for k in rows if k[2] == f"circuit_{i}"]
        assert variants[circuit_keys].nunique() == 1


def test_compute_race_signatures_and_detect_variants_end_to_end_from_raw_laps():
    rng = np.random.default_rng(2)
    rows = []
    rows += _laps_for_race(2019, 1, "bahrain", 10, (0.30, 0.35, 0.35), rng)
    rows += _laps_for_race(2020, 2, "bahrain", 10, (0.30, 0.35, 0.35), rng)
    rows += _laps_for_race(2020, 16, "bahrain", 10, (0.45, 0.30, 0.25), rng)  # short layout
    rows += _laps_for_race(2021, 3, "bahrain", 10, (0.30, 0.35, 0.35), rng)
    laps = pd.DataFrame(rows)

    signatures = circuit_variants.compute_race_signatures(laps)
    variants = circuit_variants.detect_variants(signatures, threshold=0.05)

    normal_races = [(2019, 1, "bahrain"), (2020, 2, "bahrain"), (2021, 3, "bahrain")]
    assert variants[normal_races].nunique() == 1
    assert variants[(2020, 16, "bahrain")] != variants[normal_races].iloc[0]
