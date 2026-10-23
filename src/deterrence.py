"""The measurement.

A defence that deters shots at the rim shows up in one place a public shot file
can see: opponents stop taking them. That is the whole instrument here, and it is
narrower than "defensive impact" - it says nothing about whether the shots they
do take go in, or about the possessions that end in a turnover.

Two things make the estimate honest rather than decorative.

**The comparison is within opponent.** Every Spurs game is scored against what
that opponent did in its *other* games that season. Denver takes more rim shots
than Boston does; a schedule is not a random draw; and the games one player
misses are not a random draw from the schedule either. Differencing against the
opponent's own baseline removes all of that in one step.

**Every comparison is inside a season.** Without that, a player who arrived in
one of the two seasons and was absent for the other gets handed the whole
difference between two rosters as his personal effect. Chris Paul played 82 games
for San Antonio and missed 82; both numbers are one full season, and his "on/off"
before this correction is just 2024-25 minus 2023-24.

**Every teammate gets the same treatment.** The on/off design cannot separate one
player from whatever else changed when he sat, so the same estimator is run for
every Spur who missed enough games *within a season* to support it. If the
subject's number is ordinary against that distribution, the design has found
nothing; if it sits outside it, the design has found something the roster as a
whole does not explain.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ZONES = ["Restricted Area", "In The Paint (Non-RA)", "Mid-Range",
         "Corner 3", "Above the Break 3"]
RIM, PAINT, MID, C3, ABT3 = ZONES


def game_profiles(opp: pd.DataFrame) -> pd.DataFrame:
    """One row per Spurs game: what the opponent shot, from where, and how it fell."""
    g = opp.groupby(["season", "game_id", "opponent"], observed=True)
    out = g.agg(fga=("points", "size"), pps=("points", "mean"),
                fg=("made", "mean"), date=("game_date", "first"),
                spurs_home=("is_home", lambda s: 1 - int(s.iloc[0]))).reset_index()

    counts = (opp.groupby(["season", "game_id", "zone5"], observed=False).size()
              .unstack("zone5").reindex(columns=ZONES).fillna(0))
    shares = counts.div(counts.sum(axis=1), axis=0)
    shares.columns = [f"share_{c}" for c in shares.columns]

    made = (opp.groupby(["season", "game_id", "zone5"], observed=False)["made"].mean()
            .unstack("zone5").reindex(columns=ZONES))
    made.columns = [f"fg_{c}" for c in made.columns]
    # Attempts per zone, kept so a game with two rim shots can be weighted as
    # what it is rather than treated as a 50% rim defence.
    counts.columns = [f"n_{c}" for c in counts.columns]

    out = out.merge(shares.reset_index(), on=["season", "game_id"])
    out = out.merge(made.reset_index(), on=["season", "game_id"])
    return out.merge(counts.reset_index(), on=["season", "game_id"])


def attach_expected(games: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    """Subtract what the opponent did everywhere else that season."""
    cols = ([f"share_{z}" for z in ZONES] + [f"fg_{z}" for z in ZONES] + ["pps"])
    b = baseline[["season", "opponent"] + cols].copy()
    b.columns = ["season", "opponent"] + [f"exp_{c}" for c in cols]
    m = games.merge(b, on=["season", "opponent"], how="left")
    for c in cols:
        m[f"d_{c}"] = m[c] - m[f"exp_{c}"]
    return m


def centre_within_season(games: pd.DataFrame, cols) -> pd.DataFrame:
    """Take out each season's own level, so on/off cannot become year-on-year."""
    games = games.copy()
    for c in cols:
        games[c] = games[c] - games.groupby("season")[c].transform("mean")
    return games


def weighted_effect(games: pd.DataFrame, played: frozenset, value: str,
                    weight: str) -> dict:
    """On minus off for a rate, weighting each game by its attempts.

    A game in which the opponent took three shots at the rim carries three shots
    of evidence about rim conversion, not one game of it.
    """
    def mean(sub):
        w = sub[weight].to_numpy(dtype=float)
        v = sub[value].to_numpy(dtype=float)
        ok = np.isfinite(v) & (w > 0)
        return float(np.average(v[ok], weights=w[ok])) if ok.any() else np.nan

    on = games[games["game_id"].isin(played)]
    off = games[~games["game_id"].isin(played)]
    if len(on) == 0 or len(off) == 0:
        return {}
    a, b = mean(on), mean(off)
    return {"n_on": len(on), "n_off": len(off), "on": a, "off": b, "effect": a - b}


def shot_quality(games: pd.DataFrame, zone_value: pd.Series) -> pd.DataFrame:
    """Turn a zone mix into points per shot, at fixed league-average conversion."""
    games = games.copy()
    for prefix in ("share_", "exp_share_"):
        cols = [f"{prefix}{z}" for z in ZONES]
        vals = games[cols].to_numpy() @ zone_value.reindex(ZONES).to_numpy()
        games["xq" if prefix == "share_" else "exp_xq"] = vals
    games["d_xq"] = games["xq"] - games["exp_xq"]
    return games


def within_season_split(games: pd.DataFrame, played: frozenset, minimum: int) -> bool:
    """True if some season contains enough games on both sides of the split.

    Without this, a player who joined for one of the two seasons has an on/off
    that is entirely between-season, and a bootstrap over games will hand it a
    confident interval around a number that means nothing about him.
    """
    on = games["game_id"].isin(played)
    for _, block in games.assign(on=on).groupby("season"):
        if block["on"].sum() >= minimum and (~block["on"]).sum() >= minimum:
            return True
    return False


def availability(shots: pd.DataFrame, seasons) -> pd.DataFrame:
    """Who played, inferred from who shot.

    The shot file has no minutes column, so presence is read off attempts: a
    player who took a field goal was on the floor. It misses the handful of
    appearances with no attempt, which for a rotation player is a game or two a
    year and never the difference between playing and not.
    """
    s = shots[shots["season"].isin(seasons)]
    played = (s.groupby(["player_id", "player", "season"], observed=True)["game_id"]
              .agg(lambda g: frozenset(g)).reset_index(name="games"))
    return played


def player_effect(games: pd.DataFrame, played: frozenset, metric: str) -> dict:
    """Difference in opponent-adjusted metric between games on and games off."""
    on = games[games["game_id"].isin(played)]
    off = games[~games["game_id"].isin(played)]
    if len(on) == 0 or len(off) == 0:
        return {}
    return {"n_on": len(on), "n_off": len(off),
            "on": float(on[metric].mean()), "off": float(off[metric].mean()),
            "effect": float(on[metric].mean() - off[metric].mean())}


def bootstrap_effect(games: pd.DataFrame, played: frozenset, metric: str,
                     n_boot: int, seed: int, weight: str | None = None) -> tuple:
    """Resample games within the on and off groups, which is where the noise is."""
    rng = np.random.default_rng(seed)
    on_mask = games["game_id"].isin(played).to_numpy()
    v = games[metric].to_numpy(dtype=float)
    w = (games[weight].to_numpy(dtype=float) if weight
         else np.ones(len(games), dtype=float))
    ok = np.isfinite(v) & (w > 0)
    on, on_w = v[on_mask & ok], w[on_mask & ok]
    off, off_w = v[~on_mask & ok], w[~on_mask & ok]
    if len(on) == 0 or len(off) == 0:
        return np.nan, np.nan, np.nan
    draws = np.empty(n_boot)
    for i in range(n_boot):
        ia = rng.integers(0, len(on), len(on))
        ib = rng.integers(0, len(off), len(off))
        draws[i] = (np.average(on[ia], weights=on_w[ia])
                    - np.average(off[ib], weights=off_w[ib]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    # Two-sided p by the fraction of the resampled distribution on the far side
    # of zero, doubled. Crude, and honest about being crude.
    p = 2 * min((draws >= 0).mean(), (draws <= 0).mean())
    return float(lo), float(hi), float(p)
