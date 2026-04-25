# THE SHARP MLB BETTING SYSTEM

A repeatable, edge-based framework for moneylines, run lines, totals, team totals, F5, props, live, and futures. Built for value, not vibes.

---

## 1. DAILY MLB BETTING CHECKLIST

Run this routine every day, in this order. Do not skip steps. Sharp bettors win because they are boring and consistent.

### Phase 1 — Morning (8–11 AM local)
1. Pull the day's slate, opening lines, and current lines from at least 4 books (Pinnacle, Circa, FanDuel, DraftKings) plus ESPN BET / BetMGM / Caesars for shop value.
2. Note any overnight line movement vs opening. Flag anything that moved 0.5 runs (totals), 10+ cents (ML), or where the line moved against the public majority — that is reverse line movement (RLM) and it matters.
3. Review weather forecasts for every outdoor park — wind speed/direction at first pitch, temperature at first pitch, humidity, rain probability, dew point.
4. Confirm probable starters and identify any "TBD" games — these are usually no-bet or bullpen-game spots.
5. Check umpire assignments (UmpScorecards / Swish Analytics) for K%, BB%, and run-scoring tendencies.

### Phase 2 — Midday (11 AM – 3 PM)
6. Build a pitching profile for every starter:
   - Last 3 starts: IP, pitch count, velocity (avg fastball mph), K%, BB%, HardHit%, Barrel%, CSW% (called + swinging strike rate).
   - Pitch mix vs season baseline (any major shift = command/health flag).
   - Splits vs LHB/RHB.
   - Home/road splits.
   - Park-adjusted xFIP / SIERA / xERA — not just ERA.
6b. Pull bullpen state for both teams: pitchers used yesterday, pitchers used 2+ days in a row, total bullpen pitches in last 3/7/14 days, closer availability, who is the actual high-leverage arm tonight.
7. Pull offensive context vs that pitcher's handedness:
   - Team wRC+ vs LHP/RHP last 30 days
   - Team K% vs that handedness
   - Lineup ISO and Barrel% vs that handedness
   - Top of order OBP vs that handedness

### Phase 3 — Lineup window (typically 3–5 PM ET)
8. Wait for confirmed lineups. Anything you bet before lineups carries lineup risk — price that in.
9. Recheck weather (wind shifts).
10. Recheck line — note steam moves and any sharp action signals (Pinnacle move first = sharp).

### Phase 4 — Bet execution
11. Run each game through the Grading Formula (Section 3).
12. Apply Edge Finding Rules (Section 4). Only bet plays that survive the filter.
13. Size per Bet Sizing Rules (Section 5).
14. Shop the best number across all books. The price you bet is the single biggest controllable variable in your win rate.
15. Log every bet: book, line, price, edge%, confidence, reasoning, CLV at close.

### Phase 5 — Post-game
16. Track Closing Line Value. CLV is the only short-term proof you are betting the right side. If you are consistently beating the closing line by 2–3% or more, the wins will come.

---

## 2. DATA SOURCES NEEDED

### Free / Essential
- **Baseball Savant** — Statcast: velo, barrels, xwOBA, pitch mix, run values per pitch.
- **FanGraphs** — wRC+, xFIP, SIERA, splits, leaderboards, depth charts, projected lineups.
- **Brooks Baseball / Pitcher List** — pitch-level data, release point changes (early injury tell).
- **Baseball Reference** — historical splits, matchup data, schedule context.
- **Weather.gov + Windy.com** — first-pitch forecast, gust direction at field level.
- **MLB.com lineups** — official confirmed lineups.
- **Rotowire / Lineups.com** — projected lineups + injury news.
- **UmpScorecards** — umpire K%, BB%, accuracy, run impact.
- **Swish Analytics / Evan Davis on X** — umpire tendencies and weather.

### Paid / Edge
- **Pinnacle** odds (often via OddsJam / OddsPortal / Betstamp) — sharpest market reference.
- **Unabated / OddsJam / DarkHorseOdds** — line shopping, no-vig fair odds, devig calculators, prop comparisons.
- **Sports Info Solutions / TruMedia** — defensive metrics, catcher framing runs.
- **Inpredictable / FanGraphs depth charts** — projected starters and bullpen state.
- **VSiN / Action Network** — money% vs bet%, sharp report (use carefully — much "sharp action" reporting is noise).

### Build Your Own
- **Personal bet log** (Google Sheet or Notion) — every bet, line, price, CLV, result.
- **Pitcher tracker** — last 3 starts, velo trend, pitch mix delta.
- **Bullpen usage tracker** — rolling 7-day pitch counts.

---

## 3. GAME GRADING FORMULA (0–100)

Every game gets graded across 7 weighted categories. Score each side; the difference is the edge signal. Then compare to market price.

| Category | Weight | What goes in |
|---|---|---|
| Starting Pitching Edge | 25 | xFIP, SIERA, xERA last 30d, velo trend, command (BB%, CSW%), HardHit% allowed, splits vs opponent handedness, park-adjusted |
| Bullpen Edge | 15 | Rolling 7d/14d FIP, leverage-arm availability, back-to-back usage, projected innings needed |
| Offensive Edge | 15 | Lineup wRC+ vs handedness (last 30d), team Barrel%, K% vs handedness, top-4 OBP, baserunning value |
| Weather + Park Edge | 10 | Park run factor, wind direction × speed, temp, humidity, dew point, roof state |
| Market Edge | 15 | Difference between your fair price and best available price (devig Pinnacle as anchor); RLM, steam, sharp-side indicators |
| Situational Edge | 10 | Travel, rest, getaway, day-after-night, schedule spot, motivation/standings |
| Injury + Lineup Edge | 10 | Confirmed lineup vs projection, key bat out, catcher framing, defensive alignment |

### Scoring each category
For each side, score 0–10 within the category, then multiply by weight/10. Example: pitching edge of 7 → 7 × 2.5 = 17.5 points.

### Interpreting the final score
- **75–100**: Strong play. Significant edge across multiple categories.
- **65–74**: Standard play. Real edge, normal sizing.
- **55–64**: Lean. Small play or pass if price isn't there.
- **<55**: Pass. No edge or unclear edge.

### Translating score to fair odds
Convert your projected win probability (built from the grade + a base run-environment model like a Pythagenpat / log5 expression) into decimal odds:

```
Fair decimal odds = 1 / projected win probability
Edge % = (Your fair probability × decimal odds offered) − 1
```

**Bet only if Edge % ≥ 3% on sides/totals, ≥ 5% on props, ≥ 7% on futures.** Lower thresholds are noise after vig.

---

## 4. EDGE FINDING RULES

These are the filters every potential bet must pass.

### Universal filters (all bet types)
1. **You have a number before you see the market.** If you can't generate a fair price independently, you're chasing the line.
2. **Beat the no-vig Pinnacle price by ≥ 2 cents on ML, ≥ 3% on totals/run lines, ≥ 5% on props.**
3. **Lineup is confirmed** OR the bet is robust to lineup variance (e.g., totals when both teams have stable cores).
4. **Weather is locked in** — no bet on outdoor day games with rain risk > 40% unless you're betting under and the rain is in a leverage spot.
5. **You can articulate in one sentence why the market is wrong.** If you can't, you're guessing.

### Moneyline
- Best when betting an underdog (+120 to +180 range) with a real pitching edge the public is fading on name value.
- Avoid heavy favorites (-180 or worse) unless the dog has a true bullpen game and you've grade a 10+ point pitching gap.

### Run Line (-1.5 / +1.5)
- Buy +1.5 with bad teams whose bullpens are gassed (closer unavailable).
- Sell -1.5 only when (a) ace pitcher, (b) bad opposing offense vs that handedness, (c) opponent's pen is the worst third of the league.

### Totals
- Strongest when weather + park + bullpen all point the same direction.
- **Wind out 10+ mph at Wrigley/Cincinnati/Coors → over lean.** Wind in 10+ mph anywhere → under lean.
- **Temp drop of 15°F+ from norm → under lean** (the ball doesn't carry).
- **Two gassed bullpens + above-average lineups → over.**
- **Two ace starters + cool weather → under, but the market knows this. Look for unders priced -110 or better, not -125.**

### Team Totals
- Often softer than full-game totals. If you like a side, check its team total — sometimes the value is there with less variance.
- Strong play: opponent's 5th starter / opener vs a lineup that mashes that handedness, in a hitter park.

### First 5 Innings (F5)
- Cleanest pitching bet on the board because it removes bullpen variance.
- Best edges: backing a starter the public is undervaluing because his team is bad. F5 isolates the pitching matchup.
- Use F5 totals when one bullpen is awful and the full-game total is inflated by it.

### Player Props
- Only bet props where you can construct a fair line from rate × opportunity.
  - **K props:** pitcher K/9 × projected IP, adjusted for opponent K% vs handedness and umpire K%.
  - **Hit props:** PA projection × hit rate vs that handedness, park-adjusted.
  - **HR props:** Barrel% × FB% × park HR factor × opposing pitcher HR/FB%.
  - **Total bases:** ISO vs handedness × PAs.
- Devig the alternate prop ladder to find the true market line.
- Avoid SGPs unless built around a correlated thesis (e.g., over + favorite ML when over correlates with home team scoring).

### Live Betting
- The two best live spots:
  - **First-inning overreaction:** Big favorite gives up 2 in the 1st, line swings hard. If your pre-game model still says they're the better team, hammer the new price.
  - **Bullpen reveal:** When the starter is pulled and you know the pen is gassed, attack the live total over.
- Avoid live betting tilted, in-running, without a model.

### Futures
- Only bet at +EV vs no-vig market — the vig on futures is brutal (often 20–30%).
- Best windows: early season weakness on a team with strong underlying metrics, or mid-season after an injury overcorrection.
- Hedging is correct when a future has positive EV at risk and you can lock guaranteed profit.

---

## 5. BET SIZING RULES (BANKROLL DISCIPLINE)

### Unit definition
- **1 unit = 1% of starting bankroll.** Recalibrate quarterly, not after every win or loss.
- Example: $5,000 bankroll → 1 unit = $50.

### Sizing by confidence + edge
| Edge % (vs no-vig) | Confidence (1–10) | Unit Size |
|---|---|---|
| 3–4% | 5–6 | 0.5 u |
| 4–6% | 6–7 | 1.0 u |
| 6–8% | 7–8 | 1.5 u |
| 8%+ | 9–10 | 2.0 u (rare max) |

### Half-Kelly cap
Use **half-Kelly** as the absolute maximum:
```
Kelly fraction = (decimal odds × p − 1) / (decimal odds − 1)
Bet size = 0.5 × Kelly × bankroll
```
If half-Kelly says less than 1u, trust it.

### Hard rules
- **Never exceed 2u on a single game.**
- **Never have more than 8u in action on a single slate.**
- **Never increase unit size after a loss.** Chasing is the #1 bankroll killer.
- **No parlays except:**
  - Correlated thesis with positive EV after correlation
  - Promo / boost where the boosted price is +EV vs no-vig
  - Round-robins of independent +EV singles, only if you understand the variance
- **Cash out is almost always −EV.** Use it only to lock a hedge.

---

## 6. RED FLAGS TO AVOID

If any of these are true, pass or downgrade.

1. **You only saw the line before you had a number.** You're a price-taker, not a bettor.
2. **The starter is a "TBD" or bullpen game with no announced openers.** Too much noise.
3. **Lineup risk:** a key bat is questionable, you can't confirm before bet time.
4. **Weather is unstable** — strong rain risk or shifting wind forecast.
5. **You're betting on a "narrative":** revenge, "they always cover at home," "ace bounce-back." Unless backed by data, ignore.
6. **The line moved against you and you can't explain why.** The market may know something. Re-check news.
7. **Public is heavy on your side AND the line hasn't moved.** Means books are happy to take that side. You're probably wrong.
8. **You're trying to "make money back" from yesterday.** Tilt detected.
9. **Small sample matchup history is your main reason** ("this hitter is 6-for-12 lifetime"). 12 PAs is meaningless.
10. **You're betting more than 5 games on a slate.** You don't have 5+ edges every day. Be ruthless.
11. **Heavy favorite ML on a team with a tired pen.** Bullpen risk overwhelms the implied edge.
12. **You're shopping the worst book.** If you're not on the best price, your edge is gone before the first pitch.

---

## 7. FINAL BETTING CARD TEMPLATE

Use this exact format for every recommended bet.

```
BET #X — [TEAM/PLAYER] [BET TYPE]
─────────────────────────────────
Game:           [Away] @ [Home], [Time ET]
Bet:            [e.g., Astros F5 -0.5]
Best Book:      [e.g., DraftKings -110]
Line @ Open:    [e.g., -0.5 -120]
Line Now:       [e.g., -0.5 -110]
Fair Odds:      [e.g., -125 / 55.6%]
Edge:           [e.g., +4.8%]
Confidence:     [X/10]
Risk Level:     [Low / Medium / High]
Unit Size:      [e.g., 1.0u]

Reasoning (one paragraph):
- Pitching edge: [specifics, numbers]
- Bullpen / offense / weather / market angle: [specifics]
- Why the market is wrong: [one sentence]

Pass triggers (what would make you scratch this bet):
- [e.g., key bat scratched at lineup release]
- [e.g., wind shifts in to 15+ mph]
- [e.g., line moves to -125 or worse]

CLV target:     [e.g., close at -120 or shorter]
```

---

## 8. EXAMPLE BREAKDOWN OF ONE MLB GAME

This is a synthetic walkthrough that shows the full process. Numbers are illustrative — always pull live data.

### Game: Tampa Bay Rays @ Baltimore Orioles, 7:05 PM ET
**Probables:** Shane McClanahan (LHP, TB) vs Dean Kremer (RHP, BAL)
**Park:** Camden Yards (LHB HR factor reduced post-2022 LF wall change; still hitter-friendly to RHB pull-side)
**Weather:** 74°F, wind 8 mph LF→RF (slight aid to LHB pull power), 0% rain
**Umpire:** Pat Hoberg — historically tight zone, slightly K-favorable, neutral on runs

### Step 1 — Pitching profiles
**McClanahan (last 3 starts):**
- 18.2 IP, 2.41 ERA, 2.78 xFIP, 31% K%, 6% BB%, 88 mph 4-seam (career 96 — **MAJOR RED FLAG**, possible injury or fatigue)
- HardHit% allowed last 3: 41% (career 33%) — also concerning
- Splits vs RHB this year: .312 wOBA (typically .280)
- → **Pitching edge for TB is much smaller than name suggests. Velo drop is the story.**

**Kremer (last 3 starts):**
- 17 IP, 4.24 ERA, 4.40 xFIP, 19% K%, 8% BB%, normal velo
- HR/9 last 3: 1.59 — gives up the long ball
- Splits vs LHB: .345 wOBA (TB has a heavily LHB lineup)
- → **Below-average RHP, susceptible to LHB power**

### Step 2 — Bullpens
- TB: Used Fairbanks and Adam yesterday. Closer Fairbanks unavailable for back-to-back. Middle relief depth OK. **Yellow flag.**
- BAL: Fully rested pen, top arms (Cano, Bautista) available. **Edge BAL.**

### Step 3 — Offense
- TB lineup vs RHP last 30d: 112 wRC+ (above avg), 24% K%, 8.5% Barrel%
- BAL lineup vs LHP last 30d: 119 wRC+ (well above avg), 19% K%, 9.1% Barrel%
- Both lineups are confirmed and full strength.
- → **Slight offensive edge BAL, especially given McClanahan's velo drop.**

### Step 4 — Weather + Park
- Camden plays slightly hitter-friendly. Wind aids LHB (TB has many LHBs).
- 74°F is ball-carry neutral.
- Modest tailwind for over.

### Step 5 — Market
- **Open:** TB ML -135, total 8.5
- **Now:** TB ML -120, total 9.0 (over -110)
- ML moved 15 cents toward BAL despite ~62% of public tickets on TB → **classic reverse line movement, sharp on BAL**.
- Total ticked up 0.5 — sharps and weather both pushing over.
- Pinnacle no-vig: BAL ML at +108 (implied 48.1%), Over 9 at -105 (implied 51.2%).

### Step 6 — Grading
| Category | Weight | TB Score | BAL Score |
|---|---|---|---|
| Pitching | 25 | 6/10 (15.0) | 5/10 (12.5) |
| Bullpen | 15 | 5/10 (7.5) | 7/10 (10.5) |
| Offense | 15 | 6/10 (9.0) | 7/10 (10.5) |
| Weather/Park | 10 | 5/10 (5.0) | 6/10 (6.0) |
| Market | 15 | 4/10 (6.0) | 8/10 (12.0) |
| Situational | 10 | 5/10 (5.0) | 5/10 (5.0) |
| Injury/Lineup | 10 | 6/10 (6.0) | 7/10 (7.0) |
| **Total** | | **53.5** | **63.5** |

→ BAL grades higher. Convert to win prob: estimate BAL ~52%. Best ML price: BAL +110 (DraftKings). Implied 47.6%. **Edge ≈ +4.4%.**

→ Over 9 also has multi-category support (velo drop on McClanahan + tired TB pen + Kremer HR risk + tailwind for LHB).

### Step 7 — Bet card output

```
BET #1 — BAL Orioles ML
─────────────────────────────────
Game:           TB @ BAL, 7:05 PM ET
Bet:            Orioles Moneyline
Best Book:      DraftKings +110
Line @ Open:    +125
Line Now:       +110
Fair Odds:      +92 / 52.0%
Edge:           +4.4%
Confidence:     7/10
Risk Level:     Medium
Unit Size:      1.0u

Reasoning:
- McClanahan's velocity is down 8 mph from career norms across his
  last 3 starts — this is a mechanical or health red flag the public
  is not pricing because of his name.
- BAL bullpen fully rested and is a top-5 unit; TB's closer is
  unavailable on back-to-back.
- BAL lineup posts a 119 wRC+ vs LHP over the last 30 days.
- 15-cent reverse line movement against 62% public tickets = sharp
  side.

Pass triggers:
- Key BAL bat (Henderson, Rutschman) scratched
- McClanahan's velo reportedly recovered in pregame bullpen
- Line moves to +95 or shorter

CLV target: close at +95 or shorter
```

```
BET #2 — Over 9
─────────────────────────────────
Game:           TB @ BAL, 7:05 PM ET
Bet:            Over 9
Best Book:      FanDuel -105
Line @ Open:    8.5 -110
Line Now:       9.0 -110
Fair Odds:      -120 / 54.5%
Edge:           +6.4%
Confidence:     7/10
Risk Level:     Medium
Unit Size:      1.0u

Reasoning:
- McClanahan velo drop + 41% HardHit% allowed in last 3.
- Kremer 1.59 HR/9 last 3 vs LHB-heavy lineup.
- TB pen overworked; high-leverage arms unavailable.
- 8 mph wind LF→RF aids LHB power.
- Sharp action already pushed total from 8.5 to 9 — the move is
  for the right reasons; price is still fair at -105.

Pass triggers:
- Wind reverses to in from RF
- Rain delay risk emerges
- McClanahan reportedly back to 95+ in warmups

CLV target: close at 9.5 or higher
```

### Step 8 — Total exposure check
2 bets, 1.0u each = 2.0u on the slate from this game. Within all caps. Both have independent theses (one on side, one on total) but are positively correlated (BAL covers more often when total goes over). Acceptable correlation, no sizing reduction needed since neither is a max play.

### Step 9 — Post-game
Log results, log CLV (did BAL close shorter than +110? did total close above 9.0 or with juice on over?). Process > result. A lost bet at +CLV is a good bet.

---

## QUICK-REFERENCE PRINCIPLES

1. **Beat the closing line. Everything else is noise short-term.**
2. **Shop every bet.** A 5-cent better price across a year is a 2–3% ROI swing.
3. **The pitching matchup is the most mispriced thing in baseball.** Velo and pitch mix changes are the sharpest tells.
4. **Bullpen state determines late-game and totals.** It is undervalued by the public.
5. **Weather changes totals more than lineups do.** Especially wind and temp.
6. **Lineup confirmation is non-negotiable for sides; weather lock is non-negotiable for totals.**
7. **No parlays without correlation or boosts.**
8. **2 units is your max. Ever. No exceptions.**
9. **Track everything. CLV is the truth. Results are noise across <500 bets.**
10. **The edge is in being more disciplined than the market, not smarter.**
