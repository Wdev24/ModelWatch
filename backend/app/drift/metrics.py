"""
Pure statistical drift metrics. No HTTP, no database, no ORM imports here —
this module must be usable and testable in complete isolation (spec
section 8: "The statistical core must be pure Python").
"""
import numpy as np
from scipy.stats import ks_2samp

EPSILON = 1e-4


# ---------------------------------------------------------------------------
# Numeric binning (shared by PSI and JS for numeric features)
# ---------------------------------------------------------------------------

def numeric_bin_edges(reference_values: list[float], n_bins: int = 10) -> np.ndarray:
    """
    Quantile-based bin edges derived from the reference distribution only,
    so the same bins are reused to score production data (required for a
    meaningful PSI/JS comparison). Deterministic given the same reference
    values and n_bins.
    """
    arr = np.asarray(reference_values, dtype=float)
    quantiles = np.linspace(0, 1, n_bins + 1)
    edges = np.unique(np.quantile(arr, quantiles))

    if len(edges) < 2:
        # Constant reference distribution: create a narrow central bin around
        # the reference value plus open-ended outer bins so shifted production
        # values are counted as divergence.
        center = edges[0] if len(edges) else 0.0
        edges = np.array([-np.inf, center - 0.5, center + 0.5, np.inf])
    else:
        # Open-ended outer bins ensure production values outside the
        # reference range are not silently discarded.
        edges[0] = -np.inf
        edges[-1] = np.inf

    return edges


def numeric_bin_counts(values: list[float], edges: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    counts, _ = np.histogram(arr, bins=edges)
    return counts.astype(float)


# ---------------------------------------------------------------------------
# PSI
# ---------------------------------------------------------------------------

def psi_from_counts(reference_counts: np.ndarray, production_counts: np.ndarray, epsilon: float = EPSILON) -> float:
    ref_total = reference_counts.sum()
    prod_total = production_counts.sum()
    if ref_total == 0 or prod_total == 0:
        return 0.0
    ref_pct = reference_counts / ref_total
    prod_pct = production_counts / prod_total
    ref_pct = np.where(ref_pct == 0, epsilon, ref_pct)
    prod_pct = np.where(prod_pct == 0, epsilon, prod_pct)
    return float(np.sum((prod_pct - ref_pct) * np.log(prod_pct / ref_pct)))


def psi_numeric(reference_values: list[float], production_values: list[float], n_bins: int = 10) -> float:
    edges = numeric_bin_edges(reference_values, n_bins)
    ref_counts = numeric_bin_counts(reference_values, edges)
    prod_counts = numeric_bin_counts(production_values, edges)
    return psi_from_counts(ref_counts, prod_counts)


def psi_categorical(reference_values: list[str], production_values: list[str]) -> float:
    categories = sorted(set(reference_values) | set(production_values))
    ref_counts = np.array([reference_values.count(c) for c in categories], dtype=float)
    prod_counts = np.array([production_values.count(c) for c in categories], dtype=float)
    return psi_from_counts(ref_counts, prod_counts)


# ---------------------------------------------------------------------------
# KS (numeric only)
# ---------------------------------------------------------------------------

def ks_test(reference_values: list[float], production_values: list[float]) -> tuple[float, float]:
    result = ks_2samp(np.asarray(reference_values, dtype=float), np.asarray(production_values, dtype=float))
    return float(result.statistic), float(result.pvalue)


# ---------------------------------------------------------------------------
# Jensen-Shannon divergence (normalized to [0, 1] via log base 2)
# ---------------------------------------------------------------------------

def _kl_divergence_base2(a: np.ndarray, b: np.ndarray) -> float:
    mask = a > 0
    return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))


def jensen_shannon_from_counts(reference_counts: np.ndarray, production_counts: np.ndarray, epsilon: float = EPSILON) -> float:
    ref_total = reference_counts.sum()
    prod_total = production_counts.sum()
    if ref_total == 0 or prod_total == 0:
        return 0.0
    p = reference_counts / ref_total
    q = production_counts / prod_total
    p = np.where(p == 0, epsilon, p)
    q = np.where(q == 0, epsilon, q)
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)
    return 0.5 * _kl_divergence_base2(p, m) + 0.5 * _kl_divergence_base2(q, m)


def js_numeric(reference_values: list[float], production_values: list[float], n_bins: int = 10) -> float:
    edges = numeric_bin_edges(reference_values, n_bins)
    ref_counts = numeric_bin_counts(reference_values, edges)
    prod_counts = numeric_bin_counts(production_values, edges)
    return jensen_shannon_from_counts(ref_counts, prod_counts)


def js_categorical(reference_values: list[str], production_values: list[str]) -> float:
    categories = sorted(set(reference_values) | set(production_values))
    ref_counts = np.array([reference_values.count(c) for c in categories], dtype=float)
    prod_counts = np.array([production_values.count(c) for c in categories], dtype=float)
    return jensen_shannon_from_counts(ref_counts, prod_counts)
