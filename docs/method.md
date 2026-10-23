# Method and revision notes


Does San Antonio face a different shot profile in games where Victor Wembanyama records a field-goal attempt? This study compares his first two regular seasons, 2023–24 and 2024–25, using whole-game shot files. It addresses an availability association; it does not measure his on-court defensive effect.

Each game's opponent profile is compared with that opponent's other games in the same season. Within-season centering reduces between-season roster differences. Presence is inferred from at least one recorded attempt, so appearances without an attempt can be misclassified.

## What the comparison shows

[Result table](../output/on_off.csv)

The rim-share interval includes both a decrease and an increase. This analysis therefore does not establish either deterrence or its absence. A nonsignificant result is not an equivalence test, and the teammate comparison is not a power calculation.

![Whole-game availability comparisons](../figures/02_measures.png)

The zone results are exploratory associations. The multiple-testing table reports the full family of twelve comparisons, including those that do not survive correction. The original rim-conversion and points-per-shot p-values alone are insufficient to claim confirmed effects after that correction.

[Result table](../output/multiple_tests.csv)

![Teammate availability comparisons](../figures/03_placebo.png)

Teammates share absences, opponents and lineup changes. Applying the same estimator to them reveals sensitivity to availability patterns; it neither makes them valid negative controls nor separates Wembanyama from the surrounding roster.

## A separate offensive decision

His own shot profile supports a break-even exercise: how efficient would additional rim attempts need to be to equal the field-goal points from the threes being replaced?

![Break-even shot substitution](../figures/07_breakeven.png)

This is conditional arithmetic, not an instruction to manufacture a fixed number of rim attempts. The opportunities being added may be harder than the ones already taken. Free throws, turnovers, spacing for teammates and defensive reactions are outside the calculation. The model does not estimate extra wins.

## Basketball use and next validation

The useful coaching follow-up is to review matched possessions for changes in help position and corner coverage, while separating minutes with and without the player. Whole-game shot files cannot perform that separation. The existing result can guide film questions; it cannot settle what Wembanyama causes opponents to do.

Data ends in 2024–25. This is a historical study, not a current availability report.


The result tables are linked and rendered in the main article. Full algorithms and thresholds are in `src/`; source bytes are recorded in `data/source_manifest.json`.
