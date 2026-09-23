"""Paths, constants and the handful of knobs the pipeline exposes."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "figures"
OUT = ROOT / "output"

for d in (RAW, PROC, FIG, OUT):
    d.mkdir(parents=True, exist_ok=True)

# Season label is the year the season ends: 2025 == 2024-25.
FIRST_SEASON = 2004
LAST_SEASON = 2025
SEASONS = list(range(FIRST_SEASON, LAST_SEASON + 1))

TEAM = "SAS"
TEAM_NAME = "San Antonio Spurs"
SUBJECT = "Victor Wembanyama"
WEMBY_SEASONS = [2024, 2025]

# Before 2010-11 the league logged most restricted-area attempts at the rim
# coordinate itself rather than where the shot was taken, so fine coordinates are
# not comparable across that boundary. Only the court maps depend on them; the
# zone shares that carry this project do not.
COORD_ERA_START = 2011

RIM_Y = 5.25
HEAVE_DIST = 30.0
HEAVE_SECS = 2.0

# A player counts as available in a game if he attempted a field goal in it. The
# floors below keep the placebo comparison to players with a real split on both
# sides of it.
MIN_GAMES_ON = 15
MIN_GAMES_OFF = 12
# ...and at least this many on each side inside a single season, so that a
# player who joined for one of the two years does not get the difference between
# two rosters recorded as his personal effect.
MIN_SPLIT_WITHIN = 6

N_BOOT = 4000
SEED = 20240117
