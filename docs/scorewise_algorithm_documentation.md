# ScoreWise Algorithm Documentation

## Overview

The ScoreWise algorithm is a statistical approach to basketball score prediction that analyzes historical head-to-head (H2H) matchup data and bookmaker lines to provide recommendations for Over/Under bets and team winner predictions.

## Algorithm Steps

### Step 1: Data Collection and Validation

**Requirements:**
- Minimum 6 H2H matches between the two teams
- Valid bookmaker line (match_total from odds data)
- Valid scores for all H2H matches (non-negative values)

**Validation Process:**
```python
# Check H2H data availability
if not match.h2h_matches:
    return "No H2H matches available"

# Check minimum H2H matches requirement
if len(match.h2h_matches) < 6:
    return "Insufficient H2H matches"

# Check odds data availability
if not match.odds or match.odds.match_total is None:
    return "No bookmaker line available"
```

### Step 2: H2H Total Calculation

For each H2H match, calculate the total score:
```python
h2h_totals = []
for match in h2h_matches:
    total = match.home_score + match.away_score
    h2h_totals.append(total)
```

**Example:**
- H2H Match 1: 85-92 → Total: 177
- H2H Match 2: 88-95 → Total: 183
- H2H Match 3: 91-89 → Total: 180
- H2H Match 4: 94-87 → Total: 181
- H2H Match 5: 96-93 → Total: 189
- H2H Match 6: 89-91 → Total: 180

### Step 3: Rate Value Calculation

Calculate the difference between each H2H total and the bookmaker line:
```python
rate_values = []
for total in h2h_totals:
    rate = total - bookmaker_line
    rate_values.append(rate)
```

**Example with bookmaker line = 175:**
- Rate 1: 177 - 175 = +2
- Rate 2: 183 - 175 = +8
- Rate 3: 180 - 175 = +5
- Rate 4: 181 - 175 = +6
- Rate 5: 189 - 175 = +14
- Rate 6: 180 - 175 = +5

### Step 4: Average Rate Calculation

Calculate the average rate across all H2H matches:
```python
average_rate = sum(rate_values) / len(rate_values)
```

**Example:**
Average rate = (2 + 8 + 5 + 6 + 14 + 5) / 6 = 40 / 6 = +6.67

### Step 5: Match Counting Analysis

Count matches above and below the bookmaker line:
```python
matches_above = sum(1 for total in h2h_totals if total > bookmaker_line)
matches_below = len(h2h_totals) - matches_above
```

**Example:**
- Matches above line (175): 6 out of 6
- Matches below line: 0 out of 6

### Step 6: Test Adjustments

Apply ±5 point adjustments to test prediction sensitivity:

**Decrement Test (for OVER predictions):**
```python
decrement_line = bookmaker_line - 5
decrement_test = count_matches_above(decrement_line)
```

**Increment Test (for UNDER predictions):**
```python
increment_line = bookmaker_line + 5
increment_test = total_matches - count_matches_above(increment_line)
```

**Example:**
- Decrement line: 175 - 5 = 170
- Matches above 170: 6 out of 6
- Decrement test result: 6

- Increment line: 175 + 5 = 180
- Matches above 180: 2 out of 6
- Increment test result: 6 - 2 = 4

### Step 7: Winning Pattern Analysis

Analyze H2H winning patterns and recent form:

**H2H Win Counting:**
```python
home_team_h2h_wins = count_wins_for_team(home_team, h2h_matches)
away_team_h2h_wins = count_wins_for_team(away_team, h2h_matches)
```

**Recent Form Analysis:**
- Analyze last 3 games for each team
- Calculate current winning streaks
- Consider recent performance trends

### Step 8: Prediction Rules Application

The algorithm applies the following rules to determine the recommendation:

#### OVER Bet Conditions:
1. Average rate is between +7.0 and +15.0
2. At least 3 out of 6 matches had higher scores than the bookmaker line
3. Decrement test result ≥ 1

#### UNDER Bet Conditions:
1. Average rate is between -15.0 and -7.0
2. At least 3 out of 6 matches had lower scores than the bookmaker line
3. Increment test result ≤ -1

#### NO BET:
- When average rate is between -6.0 and +6.0 (weak signals)
- OR when neither OVER nor UNDER criteria are fully satisfied

**Example Analysis:**
- Average rate: +6.67 (between -6 and +6, so NO_BET)
- Matches above line: 6/6 (meets ≥3 requirement)
- Decrement test: 6 (meets ≥1 requirement)
- **Result**: NO BET (rate too close to neutral)

### Step 9: Team Winner Prediction

Determine team winner based on H2H patterns and winning streaks:

#### HOME_TEAM Prediction:
- Home team won ≥4 out of 6 H2H games
- AND home team has winning streak ≥3

#### AWAY_TEAM Prediction:
- Away team won ≥4 out of 6 H2H games
- AND away team has winning streak ≥3

#### NO_WINNER_PREDICTION:
- When neither team meets the criteria

### Step 10: Enhanced Confidence Level Determination

The algorithm assigns confidence levels based on prediction type and winning patterns:

#### HIGH Confidence (OVER):
- Average rate between +7.0 and +15.0
- AND winning streak ≥3
- AND ≥4 H2H wins for the team

#### HIGH Confidence (UNDER):
- Average rate between -15.0 and -7.0
- AND winning streak ≥3
- AND ≥4 H2H wins for the team

#### HIGH Confidence (Team Winner):
- Winning streak ≥3 in last 3 games
- AND ≥4 H2H wins out of 6 games

#### LOW Confidence (OVER):
- Average rate between +16.0 and +20.0

#### LOW Confidence (UNDER):
- Average rate between -20.0 and -16.0

#### MEDIUM Confidence:
- All other cases that meet basic criteria but don't qualify for HIGH confidence

#### LOW Confidence (NO_BET):
- When average rate is between -6.0 and +6.0 (weak signals)
- OR when no clear pattern emerges

## Configuration Parameters

The algorithm uses the following configurable parameters:

```python
@dataclass
class ScoreWiseConfig:
    min_h2h_matches: int = 6
    over_rate_min: float = 7.0
    over_rate_max: float = 15.0
    under_rate_min: float = -15.0
    under_rate_max: float = -7.0
    test_adjustment: float = 5.0
    min_matches_above_threshold: int = 3
    
    # Team winner prediction thresholds
    min_h2h_wins_for_winner: int = 4
    min_recent_wins_for_streak: int = 3
    min_winning_streak: int = 3
```

## Algorithm Flow Summary

1. **Input Validation** → Check data requirements
2. **H2H Total Calculation** → Sum home + away scores
3. **Rate Value Calculation** → Difference from bookmaker line
4. **Average Rate Calculation** → Mean of rate values
5. **Match Counting** → Count above/below line
6. **Test Adjustments** → Apply ±5 point sensitivity tests
7. **Winning Pattern Analysis** → Analyze H2H wins and streaks
8. **Rule Application** → Apply OVER/UNDER/NO_BET logic
9. **Team Winner Prediction** → Determine winner based on patterns
10. **Enhanced Confidence Assignment** → Consider streaks and patterns
11. **Result Generation** → Create prediction object

## Example Complete Calculation

**Input Data:**
- Bookmaker line: 175
- H2H totals: [177, 183, 180, 181, 189, 180]
- H2H results: Home team won 4/6 games, current streak: 3

**Calculations:**
- Rate values: [+2, +8, +5, +6, +14, +5]
- Average rate: +6.67
- Matches above line: 6/6
- Decrement test: 6
- Increment test: 4
- Home team H2H wins: 4/6
- Home team winning streak: 3

**Analysis:**
- OVER conditions: Average rate (6.67) < minimum (7.0) ❌
- UNDER conditions: Average rate (6.67) > maximum (-7.0) ❌
- **Recommendation**: NO BET (rate between -6 and +6)
- **Team Winner**: HOME_TEAM (4/6 wins, streak: 3)
- **Confidence**: LOW (no strong statistical signal)

## Implementation Notes

- The algorithm is deterministic and will always produce the same result for identical input data
- All calculations use floating-point arithmetic for precision
- Logging is implemented at each step for debugging and analysis
- The algorithm handles edge cases gracefully (e.g., insufficient data, invalid scores)
- Results include detailed calculation metadata for transparency
- Team winner predictions are based on H2H patterns and winning streaks
- Enhanced confidence logic considers both statistical signals and winning patterns

## Mathematical Foundation

The algorithm is based on statistical principles:
- **Central tendency**: Using average rates to identify trends
- **Threshold analysis**: Using minimum/maximum bounds to filter signals
- **Sensitivity testing**: Using adjusted lines to test prediction robustness
- **Pattern recognition**: Using H2H winning patterns to predict team winners
- **Streak analysis**: Using recent form to enhance confidence scoring

This approach aims to identify statistically significant deviations from bookmaker expectations while maintaining conservative thresholds to avoid false positives, and incorporates team-specific patterns for more comprehensive predictions. 