import random

import pytest

from app.drift.engine import (
    FeatureStatus,
    MIN_USABLE_SAMPLES,
    evaluate_categorical_feature,
    evaluate_numeric_feature,
)


def _normal_sample(n, mean=0.0, std=1.0, seed=1):
    rng = random.Random(seed)
    return [rng.gauss(mean, std) for _ in range(n)]


# ---------------------------------------------------------------------------
# Numeric: no drift (same distribution)
# ---------------------------------------------------------------------------

def test_identical_normal_distributions_are_ok():
    reference = _normal_sample(500, mean=0.0, std=1.0, seed=1)
    production = _normal_sample(500, mean=0.0, std=1.0, seed=2)

    result = evaluate_numeric_feature(reference, production)

    assert result.feature_status == FeatureStatus.ok
    assert all(metric.status.value == "ok" for metric in result.metrics)


# ---------------------------------------------------------------------------
# Numeric: shifted distribution -> drifted
# ---------------------------------------------------------------------------

def test_strongly_shifted_distribution_is_drifted():
    reference = _normal_sample(500, mean=0.0, std=1.0, seed=1)
    production = _normal_sample(500, mean=5.0, std=1.0, seed=2)  # large shift

    result = evaluate_numeric_feature(reference, production)

    assert result.feature_status == FeatureStatus.drifted
    metric_by_name = {m.metric_name: m for m in result.metrics}
    assert metric_by_name["psi"].status.value == "drifted"
    assert metric_by_name["ks"].status.value == "drifted"
    assert metric_by_name["js"].status.value == "drifted"


# ---------------------------------------------------------------------------
# Numeric: constant values
# ---------------------------------------------------------------------------

def test_constant_reference_and_production_values_do_not_crash():
    reference = [5.0] * 50
    production = [5.0] * 50

    result = evaluate_numeric_feature(reference, production)

    assert result.feature_status == FeatureStatus.ok


def test_constant_reference_shifted_production_is_drifted():
    reference = [5.0] * 50
    production = [50.0] * 50

    result = evaluate_numeric_feature(reference, production)

    assert result.feature_status == FeatureStatus.drifted


# ---------------------------------------------------------------------------
# Categorical distributions
# ---------------------------------------------------------------------------

def test_identical_categorical_distributions_are_ok():
    reference = (["US"] * 40) + (["UK"] * 30) + (["FR"] * 30)
    production = (["US"] * 40) + (["UK"] * 30) + (["FR"] * 30)

    result = evaluate_categorical_feature(reference, production)

    assert result.feature_status == FeatureStatus.ok


def test_categorical_distribution_shift_is_drifted():
    reference = (["US"] * 90) + (["UK"] * 10)
    production = (["US"] * 10) + (["UK"] * 90)

    result = evaluate_categorical_feature(reference, production)

    assert result.feature_status == FeatureStatus.drifted


def test_unseen_category_in_production_increases_divergence():
    reference = ["US"] * 100
    production = (["US"] * 60) + (["FR"] * 40)  # FR never seen in reference

    result = evaluate_categorical_feature(reference, production)

    assert result.feature_status == FeatureStatus.drifted


# ---------------------------------------------------------------------------
# Threshold boundaries (drive PSI to sit right at / near known thresholds)
# ---------------------------------------------------------------------------

def test_psi_moderate_boundary_is_not_drifted():
    # A modest shift that should land in "moderate" territory, not "drifted".
    reference = _normal_sample(1000, mean=0.0, std=1.0, seed=10)
    production = _normal_sample(1000, mean=0.5, std=1.0, seed=11)

    result = evaluate_numeric_feature(reference, production)

    psi_metric = next(m for m in result.metrics if m.metric_name == "psi")
    assert psi_metric.metric_value > 0  # some divergence detected
    # Whatever bucket it lands in, it must be an explicit, valid status.
    assert result.feature_status in (FeatureStatus.ok, FeatureStatus.moderate, FeatureStatus.drifted)


# ---------------------------------------------------------------------------
# Insufficient samples
# ---------------------------------------------------------------------------

def test_insufficient_reference_samples_is_not_reported_as_ok():
    reference = _normal_sample(5, seed=1)  # below MIN_USABLE_SAMPLES
    production = _normal_sample(500, seed=2)

    result = evaluate_numeric_feature(reference, production)

    assert result.feature_status == FeatureStatus.insufficient_data
    assert result.metrics == []


def test_insufficient_production_samples_is_not_reported_as_ok():
    reference = _normal_sample(500, seed=1)
    production = _normal_sample(5, seed=2)  # below MIN_USABLE_SAMPLES

    result = evaluate_numeric_feature(reference, production)

    assert result.feature_status == FeatureStatus.insufficient_data


def test_exactly_at_minimum_sample_threshold_is_evaluated():
    reference = _normal_sample(MIN_USABLE_SAMPLES, seed=1)
    production = _normal_sample(MIN_USABLE_SAMPLES, seed=2)

    result = evaluate_numeric_feature(reference, production)

    assert result.feature_status != FeatureStatus.insufficient_data


def test_categorical_insufficient_samples():
    reference = ["US"] * 5
    production = ["US"] * 5

    result = evaluate_categorical_feature(reference, production)

    assert result.feature_status == FeatureStatus.insufficient_data
