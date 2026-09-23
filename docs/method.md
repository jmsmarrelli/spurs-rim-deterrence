# Method notes

The design, the things that went wrong before it worked, and where it is weak.

## The estimator

For each of San Antonio's games *g* against opponent *o* in season *s*, and each
measure *m* (a zone share, a conversion rate, a value):

```
d_m(g) = m(o in game g) − m(o in all its other games in season s)
```

then center `d_m` on its own season's Spurs mean, and take

```
effect = mean(d_m | subject played) − mean(d_m | subject missed)
```

Intervals come from resampling games with replacement inside each group, 4,000
draws. Conversion rates are weighted by attempts in the relevant zone, because a
game in which the opponent took three shots at the rim carries three shots of
evidence about rim defense, not one game of it.

## Three corrections, in the order I needed them

**Opponent baselines.** The first version compared what San Antonio allowed to
the league average. That is a schedule effect wearing an analysis costume: a
defense plays a specific set of opponents, and the twenty-nine other teams are
not a counterfactual for them.

**Within-season centering.** The second version compared games across both
seasons at once, and produced a placebo panel with obviously wrong entries in it
— Chris Paul and Harrison Barnes at 82 games on and 82 off, Stephon Castle at 81
and 83, all of them really measuring one season against the other rather than one
player against his absence. Centering `d_m` within season sends any purely between-season split to
zero, which is what it is worth.

**A within-season split requirement.** Centering alone is not enough: a player who
appeared in only one of the two seasons still gets an interval, and it is
confidently wrong. The placebo cohort now requires at least six games on each
side of the split *inside a single season*, which drops three players and leaves
seventeen.

## Availability without a minutes column

The shot files have no minutes and no inactive list, so a player counts as
available in a game if he attempted a field goal in it.

What this misses is an appearance with zero attempts. For a rotation player over
two seasons that is a game or two. It is worth naming rather than hiding, because
it biases in a specific direction: a player who checked in for ninety seconds and
never shot is filed as absent, which makes his "off" sample very slightly more
like his "on" sample and pulls every estimate a hair toward zero.

The cross-check available without minutes data is the count itself: Wembanyama
resolves to 71 games in 2023-24 and 46 in 2024-25, which matches the games he is
publicly recorded as playing.

## Why the placebo panel is not optional

Any on/off design confounds the player with everything correlated with his
absence. Over two seasons that includes the rest of the injury list, the trade
deadline, the coach's rotation, and — in this case — a stretch of the second
season during which the team had no reason to compete.

None of that is separable at 164 games. What *is* available is the shape of the
confound: run the same estimator on players whose presence has no plausible
bearing on where opponents shoot, and read the subject against them. That does
not identify a causal effect. It does distinguish "this is a real signal about
this player" from "this is what the estimator returns for anybody on this roster",
and on the rim-share measure it returns the second answer.

## Multiple testing

Twelve distinct tests on one player: a share and a conversion rate in each of
five zones, plus two summary measures across all of them. The four headline
measures in `output/on_off.csv` are only two additional tests, because the two
rim headlines are the restricted-area zone tests under a different name and are
counted once rather than twice — entering them twice would inflate the family
size and make the correction look more conservative than it is.

At 5% each, the expected number of false positives is 0.6. Four results cleared
0.05 before correction, which is more than chance would ordinarily hand you and
much less than four independent findings.

The whole family goes through Benjamini–Hochberg at 5%. Mid-range share
(p = 0.0005) and corner-three share (p = 0.0015) survive it. Rim conversion and
points allowed per shot, both at p = 0.027, do not. `output/multiple_tests.csv`
reports every test with its threshold, including the ones that failed.

This is the part of the project that most changes what it is safe to say. Without
the correction the natural headline is "he cuts rim conversion by three points";
with it, that result is a lead worth following rather than a finding worth
publishing.

## What I tried that did not work

**A shot-quality model instead of zone shares.** A gradient-boosted expected-value
model on coordinates gives a finer measure of the shots allowed, and at 164 games
it added nothing the five zones did not already carry while making the estimate
harder to explain. The zone version is in the repository; the model version is
not, because it did not earn its complexity here.

**Splitting by home and away.** The direction is the same on both, the samples
halve, and the intervals stop meaning anything.

**Restricting to games the subject started.** The shot files carry no lineup or
starter field, so there is no way to do this here at all. It is the check I would
run first with a play-by-play feed attached.

## Where this is weakest

**No possessions.** Everything here is per *attempt*. A defense that forces
turnovers is better than one that does not, and this data cannot see a
possession that ends without a shot. Wembanyama's block rate is exactly the kind
of event that would show up as "fewer attempts" and is invisible in a file whose
rows are attempts.

**Two seasons is not enough for the intervals to be interesting.** The
rim-conversion effect has a 95% interval running from −6.3 to −0.4 percentage
points, which is the difference between "one of the best rim protectors on
record" and "slightly better than nobody". A third season narrows it by about a
fifth, not by half — the interval scales with the square root of the sample, and
two seasons of one team's opponents is not many rim attempts. Only time fixes
this.

**The subject's absences are not random.** He missed the end of 2024-25 with a
condition that was announced mid-season. If the team's behavior changed for
other reasons at the same moment — and a team out of contention in March behaves
differently — the design absorbs that into his effect. The within-season centering
handles the level shift; it does not handle a mid-season change in how the team
played.
