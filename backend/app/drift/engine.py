"""
Drift decision layer built on top of app.drift.metrics.

Thresholds are fixed per spec section 8 and must not be changed casually:
  PSI:  0.10 = moderate, 0.25 = drifted
  KS:   statistic >= 0.20 = drifted
  JS:   0.10 = drifted

Feature-level decision: DRIFTED if any applicable metric crosses its
threshold. Insufficient usable data is a distinct, explicit status —
never silently reported as healthy.
"""
from dataclasses import dataclass, field
from enum import Enum

from app.drift import metrics as m

PSI_MODERATE_THRESHOLD = 0.10
PSI_DRIFTED_THRESHOLD = 0.25
KS_DRIFTED_THRESHOLD = 0.20
JS_DRIFTED_THRESHOLD = 0.10

# Minimum usable (valid) sample count on both sides required to compute a
# meaningful comparison. Below this, we report insufficient_data rather
# than a number that would be statistically noise.
MIN_USABLE_SAMPLES = 30


class MetricStatus(str, Enum):
    ok = "ok"
    moderate = "moderate"
    drifted = "drifted"


class FeatureStatus(str, Enum):
    ok = "ok"
    moderate = "moderate"
    drifted = "drifted"
    insufficient_data = "insufficient_data"


@dataclass
class MetricResult:
    metric_name: str
    metric_value: float
    threshold_used: float
    status: MetricStatus
    p_value: float | None = None


@dataclass
class FeatureDriftEvaluation:
    feature_status: FeatureStatus
    metrics: list[MetricResult] = field(default_factory=list)


def _psi_status(value: float) -> MetricStatus:
    if value >= PSI_DRIFTED_THRESHOLD:
        return MetricStatus.drifted
    if value >= PSI_MODERATE_THRESHOLD:
        return MetricStatus.moderate
    return MetricStatus.ok


def _ks_status(value: float) -> MetricStatus:
    return MetricStatus.drifted if value >= KS_DRIFTED_THRESHOLD else MetricStatus.ok


def _js_status(value: float) -> MetricStatus:
    return MetricStatus.drifted if value >= JS_DRIFTED_THRESHOLD else MetricStatus.ok


def _overall_status(metric_results: list[MetricResult]) -> FeatureStatus:
    if any(r.status == MetricStatus.drifted for r in metric_results):
        return FeatureStatus.drifted
    if any(r.status == MetricStatus.moderate for r in metric_results):
        return FeatureStatus.moderate
    return FeatureStatus.ok


def evaluate_numeric_feature(
    reference_values: list[float], production_values: list[float]
) -> FeatureDriftEvaluation:
    if len(reference_values) < MIN_USABLE_SAMPLES or len(production_values) < MIN_USABLE_SAMPLES:
        return FeatureDriftEvaluation(feature_status=FeatureStatus.insufficient_data, metrics=[])

    psi_value = m.psi_numeric(reference_values, production_values)
    ks_stat, ks_p = m.ks_test(reference_values, production_values)
    js_value = m.js_numeric(reference_values, production_values)

    results = [
        MetricResult("psi", psi_value, PSI_DRIFTED_THRESHOLD, _psi_status(psi_value)),
        MetricResult("ks", ks_stat, KS_DRIFTED_THRESHOLD, _ks_status(ks_stat), p_value=ks_p),
        MetricResult("js", js_value, JS_DRIFTED_THRESHOLD, _js_status(js_value)),
    ]
    return FeatureDriftEvaluation(feature_status=_overall_status(results), metrics=results)


def evaluate_categorical_feature(
    reference_values: list[str], production_values: list[str]
) -> FeatureDriftEvaluation:
    if len(reference_values) < MIN_USABLE_SAMPLES or len(production_values) < MIN_USABLE_SAMPLES:
        return FeatureDriftEvaluation(feature_status=FeatureStatus.insufficient_data, metrics=[])

    psi_value = m.psi_categorical(reference_values, production_values)
    js_value = m.js_categorical(reference_values, production_values)

    results = [
        MetricResult("psi", psi_value, PSI_DRIFTED_THRESHOLD, _psi_status(psi_value)),
        MetricResult("js", js_value, JS_DRIFTED_THRESHOLD, _js_status(js_value)),
    ]
    return FeatureDriftEvaluation(feature_status=_overall_status(results), metrics=results)
