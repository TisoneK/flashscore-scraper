# ScoreWise Prediction Calculator Algorithm

## Overview

ScoreWise is a statistical approach to basketball score prediction. The algorithm analyzes historical head-to-head (H2H) matchup data and bookmaker alternatives to provide recommendations for Over/Under bets.

---

## Algorithm Steps

### 1. Data Collection

- Gather H2H data for at least 6 previous matchups between the two teams.
- Collect bookmaker alternatives (total match score, team scores).

### 2. Statistical Analysis

- **Calculate total scores** for each historical matchup.
- **Calculate averages**:
  - Average match total
  - Average home team score
  - Average away team score
- **Calculate rate values**:
  - For each H2H match, compute the difference between the actual total score and the bookmaker's alternative (line).
- **Calculate average rates**:
  - Average the rate values across all H2H matches.
- **Perform test adjustments**:
  - Adjust the bookmaker's line by ±7 points to test the sensitivity of the prediction.

### 3. Prediction Rules

- **Over Bet**:
  - The average rate is between +7 and +20,
  - At least 4 out of 6 previous matches had higher scores than the bookmaker's line,
  - The decrement test (number of matches above the line when the line is decreased by 7) is ≥ 1.
- **Under Bet**:
  - The average rate is between -7 and -20,
  - At least 4 out of 6 previous matches had lower scores than the bookmaker's line,
  - The increment test (number of matches below the line when the line is increased by 7) is ≤ -1.
- **No Bet**:
  - When neither Over nor Under criteria are fully satisfied.

---

## Example

Suppose you have the following H2H totals and bookmaker line:

- H2H totals: 170, 175, 180, 165, 178, 172
- Bookmaker line: 172

**Step 1:** Calculate rate values:  
- 170-172 = -2  
- 175-172 = +3  
- 180-172 = +8  
- 165-172 = -7  
- 178-172 = +6  
- 172-172 = 0  

**Step 2:** Average rate:  
(-2 + 3 + 8 - 7 + 6 + 0) / 6 = +1.33

**Step 3:** Count matches above line:  
3 out of 6

**Step 4:** Test adjustments:  
- Decrement test: Bookmaker line -7 = 165, count matches above 165
- Increment test: Bookmaker line +7 = 179, count matches below 179

**Step 5:** Apply rules:  
- Average rate is not between +7 and +20 or -7 and -20, so **No Bet**.

---

## References

- [ScoreWise README](https://github.com/TisoneK/ScoreWise/blob/master/README.md)
- [ScoreWise Algorithm Documentation](https://github.com/TisoneK/ScoreWise/blob/master/scorewise_calculator_algorithm.md)
