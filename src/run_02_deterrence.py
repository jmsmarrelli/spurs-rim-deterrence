"""Stage 2 - what opponents stopped doing, and what they did anyway.

    python src/run_02_deterrence.py

Runs the on/off design over 2023-24 and 2024-25 across four measures of a
defence: where opponents shot from, whether those shots went in, the value of the
mix they ended up with, and what they actually scored. Then runs the identical
estimator on every teammate with a real within-season split, so the subject's
numbers can be read against the roster's own spread instead of against zero.

Writes output/season_profile.csv, output/game_profiles.csv, output/on_off.csv,
output/zone_breakdown.csv, output/placebo.csv and figures 01-04.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (FIG, MIN_GAMES_OFF, MIN_GAMES_ON, MIN_SPLIT_WITHIN,  # noqa: E402
                    N_BOOT, OUT, PROC, SEED, SUBJECT, WEMBY_SEASONS)
import court  # noqa: E402
import deterrence as D  # noqa: E402
import style as S  # noqa: E402

ZONES = D.ZONES
RIM = "Restricted Area"
HEADLINE = f"d_share_{RIM}"

# metric key -> (column, weight column or None, label, unit)
MEASURES = {
    "rim_share": (f"d_share_{RIM}", None,
                  "Opponent rim-shot share", "pp"),
    "rim_fg": (f"d_fg_{RIM}", f"n_{RIM}",
               "Opponent field goal percentage at the rim", "pp"),
    "shot_quality": ("d_xq", None,
                     "Value of the shot mix allowed", "pts/shot"),
    "points": ("d_pps", "fga",
               "Points allowed per shot", "pts/shot"),
}


def zone_p(games, played, col, weight):
    return D.bootstrap_effect(games, played, col, N_BOOT, SEED, weight)[2]


def benjamini_hochberg(tab: pd.DataFrame, alpha: float = 0.05) -> pd.DataFrame:
    """Control the false discovery rate across the whole family of tests."""
    d = tab.sort_values("p").reset_index(drop=True)
    m = len(d)
    d["rank"] = np.arange(1, m + 1)
    d["threshold"] = alpha * d["rank"] / m
    passing = d.index[d["p"] <= d["threshold"]]
    cut = passing.max() if len(passing) else -1
    d["survives_fdr"] = d.index <= cut
    return d


def load():
    opp = pd.read_csv(PROC / "opponent_shots.csv.gz", low_memory=False)
    sas = pd.read_csv(PROC / "spurs_shots.csv.gz", low_memory=False)
    base = pd.read_csv(PROC / "opponent_baseline.csv.gz", low_memory=False)
    zone_value = pd.read_csv(OUT / "league_zone_value.csv").set_index("zone5")["pps"]
    return opp, sas, base, zone_value


def since_year(season_tab: pd.DataFrame) -> int:
    """First season of the current unbroken run above the league line."""
    above = season_tab["rim"] > season_tab["league_rim"]
    year = season_tab.index[-1]
    for s in season_tab.index[::-1]:
        if not above.loc[s]:
            break
        year = s
    return int(year)


def fig_history(season_tab: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9.4, 5.0))
    ax.plot(season_tab.index, 100 * season_tab["league_rim"], color=S.SILVER, lw=1.8, zorder=2)
    ax.plot(season_tab.index, 100 * season_tab["rim"], color=S.SPURS, zorder=3)
    ax.scatter(season_tab.index, 100 * season_tab["rim"], s=18, color=S.SPURS,
               edgecolors=S.SURFACE, lw=1.3, zorder=4)
    for s in WEMBY_SEASONS:
        if s in season_tab.index:
            ax.scatter([s], [100 * season_tab.loc[s, "rim"]], s=80,
                       color=S.SERIES[1], edgecolors=S.SURFACE, lw=2, zorder=5)
    ax.annotate("League average", (season_tab.index[-1], 100 * season_tab["league_rim"].iloc[-1]),
                xytext=(8, -2), textcoords="offset points", va="center",
                color=S.INK_2, fontsize=9)
    ax.annotate("Spurs opponents", (season_tab.index[-1], 100 * season_tab["rim"].iloc[-1]),
                xytext=(8, 2), textcoords="offset points", va="center",
                color=S.SPURS, fontsize=9, fontweight="semibold")
    ax.annotate("Wembanyama", (WEMBY_SEASONS[0], 100 * season_tab.loc[WEMBY_SEASONS[0], "rim"]),
                xytext=(-8, 14), textcoords="offset points", ha="right",
                color=S.SERIES[1], fontsize=9, fontweight="semibold")
    ax.set_xlim(season_tab.index[0] - 0.4, season_tab.index[-1] + 4.8)
    ax.set_xticks(range(2004, 2026, 3))
    S.strip(ax)
    ax.set_ylabel("Share of opponent attempts at the rim (%)")
    ax.set_title(f"San Antonio has allowed more rim shots than the league "
                 f"every year since {since_year(season_tab) - 1}-"
                 f"{str(since_year(season_tab))[2:]}", loc="left")
    S.caption(fig, "Restricted-area share of every field goal San Antonio's opponents attempted "
                   "against them, against the same share for the league as a whole. The two "
                   "Wembanyama seasons are marked. They are better than the year before them "
                   "and still above the line.")
    fig.tight_layout()
    fig.savefig(FIG / "01_rim_share_history.png")
    plt.close(fig)


def fig_measures(results: pd.DataFrame) -> None:
    """Two panels because there are two units. One axis cannot carry both."""
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.0))
    panels = [("pp", "Percentage points", axes[0]),
              ("pts/shot", "Points per shot", axes[1])]
    for unit, xlabel, ax in panels:
        d = results[results["unit"] == unit].iloc[::-1].reset_index(drop=True)
        sig = (d["lo"] > 0) | (d["hi"] < 0)
        ax.barh(d.index, d["scaled_effect"],
                color=[S.SERIES[1] if x else S.SILVER for x in sig],
                height=0.44, zorder=2)
        ax.errorbar(d["scaled_effect"], d.index,
                    xerr=[d["scaled_effect"] - d["scaled_lo"],
                          d["scaled_hi"] - d["scaled_effect"]],
                    fmt="none", ecolor=S.INK_2, elinewidth=1.2, capsize=3.5, zorder=3)
        span = float(np.nanmax(np.abs(np.r_[d["scaled_lo"], d["scaled_hi"]])))
        fmt = "{:+.2f}" if unit == "pp" else "{:+.3f}"
        for i, r in d.iterrows():
            end = r["scaled_lo"] if r["scaled_effect"] < 0 else r["scaled_hi"]
            ax.text(end - np.sign(r["scaled_effect"] or 1) * -0.05 * span, i,
                    fmt.format(r["scaled_effect"]), va="center",
                    ha="left" if r["scaled_effect"] >= 0 else "right",
                    fontsize=9.4, color=S.INK_2, fontweight="semibold")
        ax.axvline(0, color=S.INK_3, lw=0.9, zorder=4)
        ax.set_yticks(d.index, [w.replace("Opponent ", "") for w in d["label"]])
        ax.set_xlim(-span * 1.55, span * 1.05)
        ax.set_ylim(-0.7, len(d) - 0.3)
        ax.grid(axis="y", visible=False)
        S.strip(ax, keep=("bottom",))
        ax.tick_params(axis="y", labelsize=9.2)
        ax.set_xlabel(xlabel)
    axes[0].set_title("Where they shot, and whether it went in", loc="left", pad=30)
    axes[1].set_title("What it was worth", loc="left", pad=30)
    axes[0].text(0.0, 1.04, "Orange: the 95% interval excludes zero.   Grey: it does not.",
                 transform=axes[0].transAxes, fontsize=9, color=S.INK_2)
    S.caption(fig, 'Whole-game association: games with a recorded Wembanyama attempt minus other games, adjusted for the opponent’s other games and centered within season. Bars are pointwise 95% bootstrap intervals, not multiplicity-adjusted intervals. These comparisons do not establish causality or equivalence.')
    fig.tight_layout()
    fig.savefig(FIG / "02_measures.png")
    plt.close(fig)


def fig_placebo(placebo: pd.DataFrame, metric_label: str) -> None:
    d = placebo.sort_values("effect").reset_index(drop=True)
    y = np.arange(len(d))
    colours = [S.SERIES[1] if n == SUBJECT else S.SILVER for n in d["player"]]
    fig, ax = plt.subplots(figsize=(9.2, 0.36 * len(d) + 2.8))
    ax.barh(y, 100 * d["effect"], color=colours, height=0.6, zorder=2)
    ax.errorbar(100 * d["effect"], y,
                xerr=[100 * (d["effect"] - d["lo"]), 100 * (d["hi"] - d["effect"])],
                fmt="none", ecolor=S.INK_3, elinewidth=1.0, capsize=2.5, zorder=3)
    ax.axvline(0, color=S.INK_3, lw=0.9, zorder=4)
    ax.set_yticks(y, [f"{p}   {int(o)} / {int(f)}" for p, o, f
                      in zip(d["player"], d["n_on"], d["n_off"])])
    ax.grid(axis="y", visible=False)
    S.strip(ax, keep=("bottom",))
    ax.tick_params(axis="y", labelsize=8.8)
    ax.set_xlabel(f"{metric_label}: with the player minus without (pp)")
    ax.set_title("The same estimate, run on everyone who missed enough games", loc="left")
    S.caption(fig, 'The same whole-game estimator applied to eligible teammates. Presence means a recorded attempt; labels give counts on each side. Shared absences and team context prevent these from being independent negative controls or a power calculation. Bars are pointwise 95% bootstrap intervals.')
    fig.tight_layout()
    fig.savefig(FIG / "03_placebo.png")
    plt.close(fig)


def fig_court(opp: pd.DataFrame, played: frozenset) -> None:
    sub = opp[opp["season"].isin(WEMBY_SEASONS) & (opp["y"] <= 34) & (opp["x"].abs() <= 25)]
    on, off = sub[sub["game_id"].isin(played)], sub[~sub["game_id"].isin(played)]

    cell = 1.0
    xb, yb = np.arange(-25, 26, cell), np.arange(0, 35, cell)

    def grid(d):
        xi = np.clip(np.digitize(d["x"], xb) - 1, 0, len(xb) - 2)
        yi = np.clip(np.digitize(d["y"], yb) - 1, 0, len(yb) - 2)
        n = np.zeros((len(yb) - 1, len(xb) - 1))
        np.add.at(n, (yi, xi), 1)
        return n

    non, noff = grid(on), grid(off)
    diff = 1000 * (non / non.sum() - noff / noff.sum())
    diff = np.where((non + noff) >= 10, diff, np.nan)

    cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list("div", S.DIVERGING[::-1])
    lim = float(np.nanpercentile(np.abs(diff), 97))
    fig, ax = plt.subplots(figsize=(8.9, 5.9))
    mesh = ax.pcolormesh(xb, yb, diff, cmap=cmap, vmin=-lim, vmax=lim, shading="flat", zorder=1)
    court.draw(ax, color=S.INK_3, lw=1.0, ymax=34)
    cb = fig.colorbar(mesh, ax=ax, shrink=0.62, pad=0.02)
    cb.set_label("Change in opponent attempts per 1,000", color=S.INK_2, fontsize=9)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, colors=S.INK_3, length=0)
    ax.set_title("Where opponents shot with him, and where they shot without", loc="left")
    fig.tight_layout()
    S.caption_under(fig, ax, f"Opponent shot locations in games {SUBJECT} played minus games he "
                             "missed, per 1,000 attempts, 2023-24 and 2024-25. Cells with fewer "
                             "than ten combined attempts are blank.")
    fig.savefig(FIG / "04_court_shift.png")
    plt.close(fig)


def main() -> None:
    opp, sas, base, zone_value = load()

    games = D.attach_expected(D.game_profiles(opp), base)
    games = D.shot_quality(games, zone_value)
    games.round(6).to_csv(OUT / "game_profiles.csv", index=False)

    league_rim = (base.groupby("season")
                  .apply(lambda g: np.average(g[f"share_{RIM}"], weights=g["fga"]),
                         include_groups=False))
    season_tab = (opp.groupby("season")
                  .apply(lambda g: pd.Series({
                      "rim": (g["zone5"] == RIM).mean(),
                      "paint": (g["zone5"] == "In The Paint (Non-RA)").mean(),
                      "mid": (g["zone5"] == "Mid-Range").mean(),
                      "three": g["is_three"].mean(),
                      "pps": g["points"].mean(), "fga": float(len(g))}), include_groups=False))
    season_tab["league_rim"] = league_rim
    season_tab.round(5).to_csv(OUT / "season_profile.csv")
    fig_history(season_tab)

    # --- the on/off window ---------------------------------------------
    d_cols = [c for c in games.columns if c.startswith("d_")]
    wg = D.centre_within_season(games[games["season"].isin(WEMBY_SEASONS)].copy(), d_cols)

    played = D.availability(sas, WEMBY_SEASONS)
    roster = (played.groupby(["player_id", "player"], observed=True)["games"]
              .agg(lambda s: frozenset().union(*s)).reset_index())
    subject_games = frozenset(
        roster.loc[roster["player"] == SUBJECT, "games"].iloc[0])

    rows = []
    for key, (col, weight, label, unit) in MEASURES.items():
        eff = (D.weighted_effect(wg, subject_games, col, weight) if weight
               else D.player_effect(wg, subject_games, col))
        lo, hi, p = D.bootstrap_effect(wg, subject_games, col, N_BOOT, SEED, weight)
        scale = 100.0 if unit == "pp" else 1.0
        rows.append({"metric": key, "label": label, "unit": unit, **eff,
                     "lo": lo, "hi": hi, "p": p,
                     "scaled_effect": eff["effect"] * scale,
                     "scaled_lo": lo * scale, "scaled_hi": hi * scale})
    results = pd.DataFrame(rows)
    results.round(5).to_csv(OUT / "on_off.csv", index=False)
    fig_measures(results)

    zone_rows = []
    for z in ZONES:
        share = D.player_effect(wg, subject_games, f"d_share_{z}")
        s_ci = D.bootstrap_effect(wg, subject_games, f"d_share_{z}", N_BOOT, SEED)
        fg = D.weighted_effect(wg, subject_games, f"d_fg_{z}", f"n_{z}")
        f_ci = D.bootstrap_effect(wg, subject_games, f"d_fg_{z}", N_BOOT, SEED, f"n_{z}")
        zone_rows.append({"zone": z,
                          "share_effect_pp": 100 * share["effect"],
                          "share_lo": 100 * s_ci[0], "share_hi": 100 * s_ci[1],
                          "fg_effect_pp": 100 * fg["effect"],
                          "fg_lo": 100 * f_ci[0], "fg_hi": 100 * f_ci[1]})
    zones = pd.DataFrame(zone_rows)
    zones.round(3).to_csv(OUT / "zone_breakdown.csv", index=False)

    # A family of tests was run on one player: two headline summaries plus a
    # share and a conversion rate in each of five zones. The two rim headlines
    # are the restricted-area zone tests under a different name, so they are
    # entered once, not twice - counting them twice would inflate the family
    # size and make the correction look more conservative than it is. The whole
    # family gets a Benjamini-Hochberg pass and the table reports what survives.
    specs = ([(label, col, weight) for col, weight, label, _ in MEASURES.values()]
             + [(f"{z} share", f"d_share_{z}", None) for z in ZONES]
             + [(f"{z} conversion", f"d_fg_{z}", f"n_{z}") for z in ZONES])
    seen, family_rows = set(), []
    for label, col, weight in specs:
        if (col, weight) in seen:
            continue
        seen.add((col, weight))
        family_rows.append({"label": label,
                            "p": zone_p(wg, subject_games, col, weight)})
    family = benjamini_hochberg(pd.DataFrame(family_rows))
    family.round(4).to_csv(OUT / "multiple_tests.csv", index=False)

    # --- placebo --------------------------------------------------------
    placebo_rows = []
    for _, r in roster.iterrows():
        g = frozenset(r["games"])
        eff = D.player_effect(wg, g, HEADLINE)
        if not eff or eff["n_on"] < MIN_GAMES_ON or eff["n_off"] < MIN_GAMES_OFF:
            continue
        if not D.within_season_split(wg, g, MIN_SPLIT_WITHIN):
            continue
        lo, hi, _ = D.bootstrap_effect(wg, g, HEADLINE, N_BOOT, SEED)
        placebo_rows.append({"player": r["player"], **eff, "lo": lo, "hi": hi})
    placebo = pd.DataFrame(placebo_rows).sort_values("effect")
    placebo.round(5).to_csv(OUT / "placebo.csv", index=False)
    fig_placebo(placebo, "Opponent rim-shot share")
    fig_court(opp, subject_games)

    # --- report ---------------------------------------------------------
    print(season_tab.round(4).tail(6).to_string())
    print(f"\n--- {SUBJECT}: {len(subject_games)} games played of "
          f"{wg['game_id'].nunique()} ---\n")
    print(results[["label", "unit", "on", "off", "scaled_effect",
                   "scaled_lo", "scaled_hi", "p"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("\nby zone")
    print(zones.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    print(f"\nall {len(family)} distinct tests, Benjamini-Hochberg at 5%")
    print(family[["label", "p", "threshold", "survives_fdr"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"\n--- the same rim-share estimate on {len(placebo)} Spurs ---")
    print(placebo[["player", "n_on", "n_off", "effect", "lo", "hi"]]
          .assign(effect=lambda d: 100 * d["effect"], lo=lambda d: 100 * d["lo"],
                  hi=lambda d: 100 * d["hi"])
          .to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    others = placebo.loc[placebo["player"] != SUBJECT, "effect"]
    subj = placebo.loc[placebo["player"] == SUBJECT, "effect"]
    if len(subj):
        rank = int((others < subj.iloc[0]).sum()) + 1
        print(f"\nsubject ranks {rank} of {len(placebo)} on rim-share suppression; "
              f"teammates average {100 * others.mean():+.2f} pp "
              f"with SD {100 * others.std():.2f}")


if __name__ == "__main__":
    main()
