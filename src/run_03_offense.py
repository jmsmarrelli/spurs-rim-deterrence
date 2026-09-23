"""Stage 3 - the other argument about him: should he shoot fewer threes?

    python src/run_03_offense.py

In 2024-25 Wembanyama attempted 369 above-the-break threes and 207 shots at the
rim. He is seven foot four. The argument writes itself, and the arithmetic looks
one-sided until you ask the question the arithmetic actually poses, which is not
"which shot is worth more" but "what would the *marginal* shot convert at".

His average rim attempt is worth 1.51 points. That number describes the rim
attempts a defense gave him. The rim attempts he would have to manufacture by
declining an open three are, by construction, the ones the defense did not want
to give up, and nothing in a shot file says what those are worth.

So this stage does not answer the question. It prices it: the break-even
conversion rate the extra rim attempts would need, and how the season total moves
under a range of assumptions about them.

Writes output/wemby_zones.csv, output/three_point_market.csv,
output/breakeven.csv and figures 05-07.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import FIG, OUT, PROC, SUBJECT, WEMBY_SEASONS  # noqa: E402
import deterrence as D  # noqa: E402
import labels as L  # noqa: E402
import style as S  # noqa: E402

ZONES = D.ZONES
ZONE_LABEL = {"Restricted Area": "At the rim", "In The Paint (Non-RA)": "Paint, off the rim",
              "Mid-Range": "Mid-range", "Corner 3": "Corner three",
              "Above the Break 3": "Above-the-break three"}
ABT3 = "Above the Break 3"
RIM = "Restricted Area"
MIN_FGA = 300           # to qualify for the league comparison
SHIFT_MAX = 150         # about two attempts a game
ASSUMED_RIM_FG = [0.75, 0.65, 0.55, 0.45]


def load() -> pd.DataFrame:
    pz = pd.read_csv(PROC / "player_zones.csv.gz")
    pz["pps"] = pz["pts"] / pz["fga"]
    pz["fg"] = pz["fgm"] / pz["fga"]
    return pz


def zone_table(pz: pd.DataFrame, season: int) -> pd.DataFrame:
    d = pz[pz["season"] == season]
    him = d[d["player"] == SUBJECT].set_index("zone5")
    league = (d.groupby("zone5")[["fga", "fgm", "pts"]].sum())
    league["pps"] = league["pts"] / league["fga"]
    league["share"] = league["fga"] / league["fga"].sum()
    out = pd.DataFrame({
        "fga": him["fga"], "share": him["fga"] / him["fga"].sum(),
        "pps": him["pps"], "fg": him["fg"],
        "league_share": league["share"], "league_pps": league["pps"],
    }).reindex(ZONES)
    out.index.name = "zone"
    return out


def fig_mix(tabs: dict) -> None:
    seasons = sorted(tabs)
    y = np.arange(len(ZONES))
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.6))

    ax = axes[0]
    h = 0.34
    ax.barh(y + h / 2 + 0.02, 100 * tabs[seasons[-1]]["share"].to_numpy(),
            height=h, color=S.SPURS, zorder=2)
    ax.barh(y - h / 2 - 0.02, 100 * tabs[seasons[-1]]["league_share"].to_numpy(),
            height=h, color=S.SILVER, zorder=2)
    for i, (a, b) in enumerate(zip(tabs[seasons[-1]]["share"],
                                   tabs[seasons[-1]]["league_share"])):
        ax.text(100 * a + 0.6, i + h / 2 + 0.02, f"{100 * a:.0f}", va="center",
                fontsize=9, color=S.INK_2, fontweight="semibold")
        ax.text(100 * b + 0.6, i - h / 2 - 0.02, f"{100 * b:.0f}", va="center",
                fontsize=9, color=S.INK_3)
    ax.set_yticks(y, [ZONE_LABEL[z] for z in ZONES])
    ax.set_ylim(-0.7, len(ZONES) - 0.3)
    ax.grid(axis="y", visible=False)
    S.strip(ax, keep=("bottom",))
    ax.tick_params(axis="y", labelsize=9.2)
    ax.set_xlabel("Share of his own attempts (%)")
    ax.set_title(f"Where he shot, {seasons[-1] - 1}-{str(seasons[-1])[2:]}",
                 loc="left", pad=28)
    ax.text(0.0, 1.03, "Black: Wembanyama.   Grey: the league.",
            transform=ax.transAxes, fontsize=9, color=S.INK_2)

    ax = axes[1]
    t = tabs[seasons[-1]]
    for i, z in enumerate(ZONES):
        ax.plot([t.loc[z, "league_pps"], t.loc[z, "pps"]], [i, i],
                color=S.GRID, lw=2.6, zorder=1)
    ax.scatter(t["league_pps"], y, s=76, color=S.SILVER, edgecolors=S.SURFACE,
               lw=2, zorder=3)
    ax.scatter(t["pps"], y, s=76, color=S.SPURS, edgecolors=S.SURFACE, lw=2, zorder=3)
    for i, z in enumerate(ZONES):
        far = max(t.loc[z, "pps"], t.loc[z, "league_pps"])
        ax.text(far + 0.03, i, f"{t.loc[z, 'pps']:.2f}", va="center",
                fontsize=9, color=S.INK_2, fontweight="semibold")
    ax.set_yticks(y, [f"{int(n)} att." for n in t["fga"]])
    ax.set_ylim(-0.7, len(ZONES) - 0.3)
    ax.grid(axis="y", visible=False)
    S.strip(ax, keep=("bottom",))
    ax.tick_params(axis="y", labelsize=9)
    ax.set_xlabel("Points per attempt")
    ax.set_title("What each one was worth to him", loc="left", pad=28)
    ax.text(0.0, 1.03, "Black: his rate.   Grey: the league's rate from the same zone.",
            transform=ax.transAxes, fontsize=9, color=S.INK_2)

    S.caption(fig, "Regular season field goal attempts only; free throws are not in this data, "
                   "which understates every drive and every post-up. His rim attempts are worth "
                   "more than the league's; his above-the-break threes are worth about the same.")
    fig.tight_layout()
    fig.savefig(FIG / "05_shot_mix.png")
    plt.close(fig)


def fig_market(pz: pd.DataFrame, season: int) -> None:
    d = pz[(pz["season"] == season) & (pz["zone5"] == ABT3)].copy()
    totals = pz[pz["season"] == season].groupby("player")["fga"].sum()
    d["total_fga"] = d["player"].map(totals)
    d = d[(d["total_fga"] >= MIN_FGA) & (d["fga"] >= 100)]

    fig, ax = plt.subplots(figsize=(9.6, 6.0))
    ax.scatter(d["fga"], d["pps"], s=16, c=S.SILVER, lw=0, alpha=0.85, zorder=2)
    league_pps = d["pts"].sum() / d["fga"].sum()
    ax.axhline(league_pps, color=S.INK_3, lw=1.0, zorder=3)
    ax.annotate("Average above-the-break three", (d["fga"].max(), league_pps),
                xytext=(-4, 7), textcoords="offset points", ha="right",
                fontsize=8.6, color=S.INK_3)

    him = d[d["player"] == SUBJECT]
    ax.scatter(him["fga"], him["pps"], s=90, c=S.SERIES[1],
               edgecolors=S.SURFACE, lw=2, zorder=5)
    tag = pd.concat([d.nlargest(6, "fga"), him]).drop_duplicates("player")
    others = tag[tag["player"] != SUBJECT]
    ax.scatter(others["fga"], others["pps"], s=34, c=S.SPURS,
               edgecolors=S.SURFACE, lw=1.4, zorder=4)
    S.strip(ax)
    ax.set_xlabel("Above-the-break three-point attempts")
    ax.set_ylabel("Points per attempt")
    ax.set_title(f"He shoots them like a guard, {season - 1}-{str(season)[2:]}", loc="left")
    fig.tight_layout()
    L.place(ax, tag["fga"], tag["pps"], tag["player"], colour=S.INK)
    S.caption(fig, f"Players with {MIN_FGA}+ total attempts and 100+ above the break. The six "
                   "highest-volume shooters are named, and so is he. Volume like that from a "
                   "center is the thing without precedent here, not the accuracy.")
    fig.savefig(FIG / "06_three_point_market.png")
    plt.close(fig)


def breakeven(tab: pd.DataFrame) -> pd.DataFrame:
    """How the season total moves if some threes become rim attempts."""
    abt3_pps = float(tab.loc[ABT3, "pps"])
    rows = []
    for fg in ASSUMED_RIM_FG:
        for n in range(0, SHIFT_MAX + 1, 5):
            rows.append({"assumed_rim_fg": fg, "shifted": n,
                         "points_gained": n * (2 * fg - abt3_pps)})
    out = pd.DataFrame(rows)
    out.attrs["breakeven_fg"] = abt3_pps / 2
    out.attrs["abt3_pps"] = abt3_pps
    return out


def fig_breakeven(be: pd.DataFrame, tab: pd.DataFrame, season: int) -> None:
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    for i, fg in enumerate(ASSUMED_RIM_FG):
        d = be[be["assumed_rim_fg"] == fg]
        ax.plot(d["shifted"], d["points_gained"], color=S.SERIES[i], zorder=3)
        ax.annotate(f"{100 * fg:.0f}%", (d["shifted"].iloc[-1], d["points_gained"].iloc[-1]),
                    xytext=(7, 0), textcoords="offset points", va="center",
                    color=S.SERIES[i], fontsize=9.5, fontweight="semibold")
    ax.axhline(0, color=S.INK_3, lw=1.0, zorder=2)
    be_fg = be.attrs["breakeven_fg"]
    ax.text(0.02, 0.30,
            f"Break-even: a traded attempt has to go in\n"
            f"{100 * be_fg:.1f}% of the time to be worth making.\n"
            f"His actual rate at the rim was "
            f"{100 * tab.loc[RIM, 'fg']:.1f}%.",
            transform=ax.transAxes, fontsize=9.5, color=S.INK_2, va="top",
            linespacing=1.6)
    S.strip(ax)
    ax.set_xlim(0, SHIFT_MAX + 22)
    ax.set_xlabel("Above-the-break threes traded for shots at the rim, over a season")
    ax.set_ylabel("Points gained")
    ax.set_title("The question is not which shot is better. It is what the next one converts at.",
                 loc="left", pad=30)
    ax.text(0.0, 1.035, "Each line assumes the traded attempts convert at that rate.",
            transform=ax.transAxes, fontsize=9, color=S.INK_2)
    S.caption(fig, f"{season - 1}-{str(season)[2:]}. Free throws are excluded, which biases this "
                   "against the rim: attacking it draws fouls that a field goal file cannot see. "
                   "So does anything his shooting does to the space his teammates play in, which "
                   "biases it the other way.")
    fig.tight_layout()
    fig.savefig(FIG / "07_breakeven.png")
    plt.close(fig)


def main() -> None:
    pz = load()
    tabs = {s: zone_table(pz, s) for s in WEMBY_SEASONS}
    latest = WEMBY_SEASONS[-1]

    frames = []
    for s, t in tabs.items():
        f = t.reset_index()
        f.insert(0, "season", s)
        frames.append(f)
    pd.concat(frames).round(5).to_csv(OUT / "wemby_zones.csv", index=False)

    fig_mix(tabs)
    fig_market(pz, latest)

    be = breakeven(tabs[latest])
    be.round(3).to_csv(OUT / "breakeven.csv", index=False)
    fig_breakeven(be, tabs[latest], latest)

    market = pz[(pz["season"] == latest) & (pz["zone5"] == ABT3)].copy()
    totals = pz[pz["season"] == latest].groupby("player")["fga"].sum()
    market["total_fga"] = market["player"].map(totals)
    market = market[(market["total_fga"] >= MIN_FGA) & (market["fga"] >= 100)]
    market.round(4).to_csv(OUT / "three_point_market.csv", index=False)

    for s in WEMBY_SEASONS:
        print(f"\n--- {SUBJECT}, {s - 1}-{str(s)[2:]} ---")
        print(tabs[s].round(4).to_string())

    t = tabs[latest]
    print(f"\nabove-the-break threes {int(t.loc[ABT3, 'fga'])}, "
          f"attempts at the rim {int(t.loc[RIM, 'fga'])}")
    print(f"points per attempt: three {t.loc[ABT3, 'pps']:.3f}, rim {t.loc[RIM, 'pps']:.3f}")
    print(f"break-even conversion on a traded attempt: "
          f"{100 * be.attrs['breakeven_fg']:.1f}%   "
          f"his actual rim conversion: {100 * t.loc[RIM, 'fg']:.1f}%")
    for fg in ASSUMED_RIM_FG:
        gain = SHIFT_MAX * (2 * fg - t.loc[ABT3, "pps"])
        print(f"  trading {SHIFT_MAX} threes at an assumed {100 * fg:.0f}% rim rate: "
              f"{gain:+.0f} points over the season")

    rank = (market["pps"] > t.loc[ABT3, "pps"]).sum() + 1
    print(f"\namong {len(market)} qualified shooters, he ranks {rank} in points per "
          f"above-the-break three and {(market['fga'] > t.loc[ABT3, 'fga']).sum() + 1} in volume")


if __name__ == "__main__":
    main()
