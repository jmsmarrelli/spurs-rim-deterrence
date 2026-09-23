# Data

One CSV per season at `data/raw/NBA_<season>_Shots.csv`, where `<season>` is the
year the season ended: `NBA_2025_Shots.csv` is 2024-25.

## Getting the files

```bash
git clone --depth 1 https://github.com/DomSamangy/NBA_Shots_04_24.git /tmp/nba_shots
for z in /tmp/nba_shots/NBA_*_Shots.csv.zip; do unzip -o -q "$z" -d data/raw/; done
```

About 850 MB unzipped. `data/raw/` and `data/processed/` are gitignored;
everything the analysis cites is written to `output/` and committed.

## Two things the raw files will do to you

**Three seasons are on a different coordinate scale.** 2019-20, 2020-21 and
2021-22 store x divided by ten, and y divided by ten and shifted by the rim
offset. `features.normalise_coordinates` detects the compression and inverts it;
the repair is cross-checked against the files' own `SHOT_DISTANCE` column, which
agrees to within half a foot in all twenty-two seasons afterwards and is off by
twelve feet in those three before.

**Coordinates are not comparable across 2010-11.** Before that season most
restricted-area attempts carry the rim's own coordinate rather than the
shooter's, so 26-27% of all attempts sit at exactly zero feet against 7-11%
afterwards. Nothing in this project compares fine coordinates across that
boundary — the zone labels the analysis runs on are coarse enough to be
unaffected, and the only court map is drawn inside the two Wembanyama seasons.

## Columns used

| Column | Used for |
|---|---|
| `SEASON_1` | season, labeled by ending year |
| `GAME_ID` | identifying Spurs games, and the on/off split |
| `PLAYER_ID`, `PLAYER_NAME` | availability, and the subject's own shot diet |
| `TEAM_NAME`, `HOME_TEAM`, `AWAY_TEAM` | which side of the game a shot belongs to |
| `LOC_X`, `LOC_Y` | the court map |
| `SHOT_TYPE`, `BASIC_ZONE` | the five zones the analysis runs on |
| `QUARTER`, `MINS_LEFT`, `SECS_LEFT` | the heave filter |
| `SHOT_MADE` | conversion |
