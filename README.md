# gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Vellocatta/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Vellocatta/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Tier-filtered comparable-shape forecaster for GTA VI's launch-day Twitch concurrent viewers, hours 2–24, as five log-scale quantiles (0.05, 0.25, 0.5, 0.75, 0.95) anchored on the case's hour-1 print.

Method: an ensemble of two comparable-based views, averaged in log space. (A) Ratio view — the empirical quantiles of the log ratios ln(viewers_h / viewers_1) across the 8 clean comparables whose hour-1 print is closest in log to the case's. (B) Peak view — the neighbours' median log release-day peak times their median peak-normalised shape, with the peak spread and shape spread combined in quadrature as normal quantiles. Only "clean" comparables are used: launches whose notes say they had an early-access window or call them weak are dropped, because their release-day curves are distorted (their peak happened days before release day). Everything is computed at run time from the case file itself, so the same program works on the practice cases and the final case. No network, no clock, no randomness; Python 3.13 standard library only.

Practice validation (mean pinball loss on the log scale, scored against the true hourly prints): p00 0.224, p01 0.129, p02 0.110, p03 0.182 — mean 0.161, against the house baseline's 0.387 (0.744 / 0.287 / 0.215 / 0.303). The median stays near the empirical centre; the edge is the shape and the volatility-adaptive width, not a centre tilt.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=55z7zxas&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
