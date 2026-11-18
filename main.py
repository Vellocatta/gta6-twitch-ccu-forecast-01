"""gta6-twitch-ccu-forecast-01 entry: tier-filtered comparable-shape forecaster.

Forecasts hours 2..24 of a game's launch day on Twitch as five log-scale
quantiles (0.05, 0.25, 0.5, 0.75, 0.95), anchored on the case's hour-1 print.

Method (an ensemble of two comparable-based views, averaged in log space):

  A. Ratio view. Take the K=8 clean comparables whose hour-1 print is closest
     in log to the case's hour-1 print, and read off the empirical quantiles
     of their log ratios ln(viewers_h / viewers_1) at each hour h. This is the
     honest predictive distribution of the day's shape given games of the same
     launch scale.

  B. Peak view. From the same 8 neighbours, take the median of their log
     release-day peaks and the median of their peak-normalised shapes
     ln(viewers_h / peak). The forecast median is the neighbour-median peak
     times the median shape; the spread is the peak spread and the shape
     spread combined in quadrature, as normal quantiles. This view is steadier
     in the evening, where the peak-normalised shape is tight.

  The two views are averaged in log space (geometric mean of each quantile).
  The median stays near the empirical centre; the edge is the shape and the
  volatility-adaptive width, not a centre tilt.

Only "clean" comparables are used: a comparable whose unlock notes say it had
an early-access window ("early-access-contaminated") or call it weak
("Tier: weak") is dropped, because its release-day curve is distorted (its
peak happened days before release day). The game's own pre-release category
history has no release day, so it drops out naturally (no hour 1).

Everything is computed at run time from the case file itself, so the same
program works on the practice cases (38 comparables) and the final case
(42 comparables, including the four practice launches). No fitted constants
are baked in beyond K and the level list; no network, no clock, no randomness.

Fallback: if fewer than two clean comparables survive, fall back to the
house-style persistence forecast (median = hour-1 print, spread widening
like a random walk in log space), so the program always writes a valid file.

Python 3.13, standard library only. Run as:
    mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

# Ensemble in one line: the ratio view and the peak view are averaged in log
# space, so the forecast inherits the ratio view's honest day-shape and the
# peak view's steadier evening, with the median kept near the empirical centre.
import json
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.644854, -0.67449, 0.0, 0.67449, 1.644854]
K = 8
BASE_SIGMA = 0.15


def round2(x: float) -> float | int:
    """Round to 2 decimals, half up (like JavaScript's Math.round(x*100)/100)."""
    scaled = x * 100.0
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100.0
    return int(value) if value == int(value) else value


def pct(values, q: float) -> float:
    """Linear-interpolation percentile of a non-empty list."""
    v = sorted(values)
    n = len(v)
    if n == 1:
        return v[0]
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = min(n - 1, lo + 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def pstdev(values, mean: float) -> float:
    if len(values) < 2:
        return 0.0
    return math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))


def parse_time(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def comparable_day(comp: dict):
    """Extract a comparable's release-day hourly series.

    Returns (hour -> viewers, peak) or None when the release day is
    incomplete (the target game's own pre-release history has no release
    day yet) or the hour-1 print is not positive.
    """
    day_start = parse_time(comp["day_start"])
    by_hour = {}
    for pt in comp["hourly"]:
        t = parse_time(pt["from"])
        if day_start <= t < day_start + timedelta(days=1):
            by_hour[t.hour + 1] = pt["viewers"]
    if 1 not in by_hour or not by_hour[1] or by_hour[1] <= 0:
        return None
    for h in range(2, 25):
        if h not in by_hour or not by_hour[h] or by_hour[h] <= 0:
            return None
    return by_hour, max(by_hour[h] for h in range(1, 25))


def clean_comparables(case: dict):
    """Usable comparables, minus early-access-contaminated and weak ones."""
    out = []
    for comp in case["comparables"]:
        unlock = comp.get("unlock", "") or ""
        if "early-access-contaminated" in unlock or "Tier: weak" in unlock:
            continue
        got = comparable_day(comp)
        if got is None:
            continue
        by_hour, peak = got
        out.append({"name": comp["name"], "by_hour": by_hour,
                    "peak": peak, "p1": by_hour[1]})
    return out


def neighbours(comps, p1: float, k: int):
    """The k comparables whose hour-1 print is closest in log to p1."""
    lp = math.log(p1)
    ranked = sorted(comps, key=lambda c: (abs(math.log(c["p1"]) - lp), c["name"]))
    return ranked[:k]


def ratio_view(near, p1: float):
    """Empirical quantiles of neighbours' log ratios, per hour."""
    rows = {}
    for h in range(2, 25):
        vals = [math.log(c["by_hour"][h] / c["p1"]) for c in near]
        rows[h] = [pct(vals, q) for q in LEVELS]
    return rows


def peak_view(near, p1: float):
    """Neighbour-median peak times median peak-normalised shape, normal spread."""
    logpeaks = [math.log(c["peak"]) for c in near]
    logpeak = pct(logpeaks, 0.5)
    peak_sd = pstdev(logpeaks, sum(logpeaks) / len(logpeaks))
    rows = {}
    for h in range(2, 25):
        vals = [math.log(c["by_hour"][h] / c["peak"]) for c in near]
        med = pct(vals, 0.5)
        shape_sd = pstdev(vals, sum(vals) / len(vals))
        spread = math.sqrt(shape_sd * shape_sd + peak_sd * peak_sd)
        centre = logpeak - math.log(p1) + med
        rows[h] = [centre + z * spread for z in Z]
    return rows


def ensemble(rows_a, rows_b):
    """Log-average of two per-hour quantile rows (geometric mean)."""
    # Averaging in log space keeps every quantile positive and lets the
    # steadier peak view pull the ratio view's wide evening tails inward.
    out = {}
    for h in range(2, 25):
        out[h] = [(a + b) / 2.0 for a, b in zip(rows_a[h], rows_b[h])]
    return out


def persistence_rows(p1: float):
    rows = {}
    for h in range(2, 25):
        rows[h] = [z * BASE_SIGMA * math.sqrt(h - 1) for z in Z]
    return rows


def clamp_quantiles(log_qs, p1: float):
    qs = []
    for v in log_qs:
        q = p1 * math.exp(v)
        q = min(max(q, 1.0), 1e9)
        qs.append(round2(q))
    for i in range(1, 5):
        if qs[i] < qs[i - 1]:
            qs[i] = qs[i - 1]
    return qs


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))
    try:
        comps = clean_comparables(case)
        if len(comps) < 2:
            raise ValueError("too few clean comparables")
        near = neighbours(comps, p1, K)
        if len(near) < 2:
            raise ValueError("too few neighbours")
        rows = ensemble(ratio_view(near, p1), peak_view(near, p1))
    except Exception:
        rows = persistence_rows(p1)
    return {"hours": [{"hour": h, "q": clamp_quantiles(rows[h], p1)}
                    for h in range(2, 25)]}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
