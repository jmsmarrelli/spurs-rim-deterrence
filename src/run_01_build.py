"""Stage 1 - pull every shot taken in a Spurs game, and the baseline to judge it against.

    python src/run_01_build.py

Three things come out of one pass over the raw season files:

* every shot San Antonio's opponents took against them, 2003-04 to 2024-25;
* every shot San Antonio took;
* for each opponent in each season, the shot profile it produced **in its other
  games** - the games that did not involve San Antonio.

That third table is the point. Comparing the shots a defense allows against the
league average asks the wrong question, because a defense does not play the
league average: it plays a specific schedule, and the games one player misses are
not a random draw from it. The counterfactual for "what would Denver have shot
here" is what Denver shot everywhere else that year.

Writes data/processed/opponent_shots.csv.gz, spurs_shots.csv.gz,
opponent_baseline.csv.gz and output/build_audit.csv.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import OUT, PROC, RAW, SEASONS, TEAM, WEMBY_SEASONS  # noqa: E402
import features  # noqa: E402

ZONES = ["Restricted Area", "In The Paint (Non-RA)", "Mid-Range",
         "Corner 3", "Above the Break 3"]
KEEP = ["season", "game_id", "game_date", "team_abbrev", "player", "player_id",
        "x", "y", "dist", "is_three", "zone5", "made", "points", "is_home"]


def zone5(zone: pd.Series) -> pd.Categorical:
    """Left and right corner threes are the same shot; everything else is as filed."""
    z = zone.astype(str).replace({"Left Corner 3": "Corner 3", "Right Corner 3": "Corner 3"})
    return pd.Categorical(z, categories=ZONES, ordered=True)


def profile(df: pd.DataFrame) -> pd.Series:
    """Zone shares, and conversion in each zone, for any set of attempts.

    Both halves are needed. Where a team shoots from and whether those shots go
    in are different questions about a defense, and the whole point of this
    project is that they can move in different directions.
    """
    n = len(df)
    shares = df["zone5"].value_counts(normalize=True).reindex(ZONES).fillna(0.0)
    fg = df.groupby("zone5", observed=False)["made"].mean().reindex(ZONES)
    out = {f"share_{z}": shares[z] for z in ZONES}
    out.update({f"fg_{z}": fg[z] for z in ZONES})
    out.update(fga=n, pps=df["points"].mean(), fg=df["made"].mean(),
               three_rate=df["is_three"].mean())
    return pd.Series(out)


def main() -> None:
    opp_frames, sas_frames, base_frames, player_frames, audit = [], [], [], [], []
    zone_made, zone_att = pd.Series(0.0, index=ZONES), pd.Series(0.0, index=ZONES)

    for season in SEASONS:
        path = RAW / f"NBA_{season}_Shots.csv"
        if not path.exists():
            print(f"  missing {path.name} - skipping", file=sys.stderr)
            continue
        t0 = time.time()
        raw = pd.read_csv(path, low_memory=False)
        tidy = features.build(raw)
        # Filter first, then bucket: the backcourt rows that the heave filter
        # removes are the only ones outside the five zones.
        rescaled = tidy.attrs.get("rescaled", False)
        tidy = tidy.loc[~tidy["excluded"]].copy()
        tidy["zone5"] = zone5(tidy["zone"])
        tidy = tidy[KEEP]

        zone_made = zone_made.add(tidy.groupby("zone5", observed=True)["made"].sum(),
                                  fill_value=0)
        zone_att = zone_att.add(tidy.groupby("zone5", observed=True).size(), fill_value=0)

        # Games involving San Antonio, from the shot rows themselves.
        sas_games = set(tidy.loc[tidy["team_abbrev"].astype(str) == TEAM, "game_id"])
        in_sas = tidy["game_id"].isin(sas_games)
        is_sas = tidy["team_abbrev"].astype(str) == TEAM

        sas_frames.append(tidy[is_sas])
        opp = tidy[in_sas & ~is_sas].copy()
        opp["opponent"] = opp["team_abbrev"].astype(str)
        opp_frames.append(opp)

        # Each team's own profile in the games it did NOT play San Antonio.
        elsewhere = tidy[~in_sas]
        base = (elsewhere.groupby(elsewhere["team_abbrev"].astype(str), observed=True)
                .apply(profile, include_groups=False).reset_index())
        base = base.rename(columns={base.columns[0]: "opponent"})
        base.insert(0, "season", season)
        base_frames.append(base)

        # Every player's zone-by-zone line in the seasons the subject played, so
        # stage 3 can put him next to the rest of the league rather than next to
        # a league average that includes nobody like him.
        if season in WEMBY_SEASONS:
            pz = (tidy.groupby(["season", "player_id", "player", "zone5"], observed=True)
                  .agg(fga=("made", "size"), fgm=("made", "sum"),
                       pts=("points", "sum")).reset_index())
            player_frames.append(pz)

        audit.append({"season": season, "shots": len(tidy),
                      "spurs_games": len(sas_games),
                      "opponent_shots": int((in_sas & ~is_sas).sum()),
                      "spurs_shots": int(is_sas.sum()),
                      "coords_rescaled": bool(rescaled)})
        print(f"  {season}  {len(sas_games):>2} Spurs games  "
              f"{int((in_sas & ~is_sas).sum()):>5} opponent shots  "
              f"({time.time() - t0:.1f}s)")

    if not opp_frames:
        raise SystemExit("No raw season files found. See data/README.md.")

    opp = pd.concat(opp_frames, ignore_index=True)
    sas = pd.concat(sas_frames, ignore_index=True)
    base = pd.concat(base_frames, ignore_index=True)

    opp.to_csv(PROC / "opponent_shots.csv.gz", index=False, compression="gzip")
    sas.to_csv(PROC / "spurs_shots.csv.gz", index=False, compression="gzip")
    base.round(6).to_csv(PROC / "opponent_baseline.csv.gz", index=False, compression="gzip")

    league = pd.DataFrame({"zone5": ZONES,
                           "fga": zone_att.reindex(ZONES).to_numpy(),
                           "fg": (zone_made / zone_att).reindex(ZONES).to_numpy()})
    league["pps"] = league["fg"] * np.where(
        league["zone5"].isin(["Corner 3", "Above the Break 3"]), 3.0, 2.0)
    league.round(6).to_csv(OUT / "league_zone_value.csv", index=False)

    if player_frames:
        pd.concat(player_frames, ignore_index=True).to_csv(
            PROC / "player_zones.csv.gz", index=False, compression="gzip")

    pd.DataFrame(audit).to_csv(OUT / "build_audit.csv", index=False)
    print(f"\n{len(opp):,} opponent shots and {len(sas):,} Spurs shots across "
          f"{opp['game_id'].nunique():,} games, {opp.season.min()}-{opp.season.max()}")
    print("\nleague-wide value of a shot from each zone, pooled over all seasons")
    print(league.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
