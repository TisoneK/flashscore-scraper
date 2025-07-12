# Prediction Table Example

## Enhanced ScoreWise Algorithm Results

This document shows an example of how the prediction table would look with the enhanced ScoreWise algorithm that includes team winner predictions and improved confidence logic.

---

## Example Prediction Table

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                            Prediction Results                                                        │
├─────────────┬──────────────┬──────────────┬──────┬──────┬────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│ Date/Time   │ Home         │ Away         │ Line │ AVG  │ RATIO  │ Prediction│ Winner   │ Conf.    │ AvgRate  │ Match ID │
├─────────────┼──────────────┼──────────────┼──────┼──────┼────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 15/01/2024  │ Lakers       │ Warriors     │ 225  │ 237  │ 5/6    │ OVER     │ HOME_TEAM│ HIGH     │ +12.5    │ LAK_001  │
│ (14:00)     │              │              │      │      │        │          │          │          │          │          │
├─────────────┼──────────────┼──────────────┼──────┼──────┼────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 15/01/2024  │ Celtics      │ Heat         │ 218  │ 207  │ 4/6    │ UNDER    │ AWAY_TEAM│ HIGH     │ -11.2    │ CEL_002  │
│ (16:30)     │              │              │      │      │        │          │          │          │          │          │
├─────────────┼──────────────┼──────────────┼──────┼──────┼────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 15/01/2024  │ Bulls        │ Nets         │ 212  │ 216  │ 3/6    │ NO_BET   │ NO_BET   │ LOW      │ +3.8     │ BUL_003  │
│ (19:00)     │              │              │      │      │        │          │          │          │          │          │
├─────────────┼──────────────┼──────────────┼──────┼──────┼────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 15/01/2024  │ Suns         │ Clippers     │ 220  │ 229  │ 4/6    │ OVER     │ HOME_TEAM│ MEDIUM   │ +9.3     │ SUN_004  │
│ (20:30)     │              │              │      │      │        │          │          │          │          │          │
├─────────────┼──────────────┼──────────────┼──────┼──────┼────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 15/01/2024  │ Nuggets      │ Jazz         │ 215  │ 196  │ 5/6    │ UNDER    │ NO_BET   │ LOW      │ -18.7    │ NUG_005  │
│ (22:00)     │              │              │      │      │        │          │          │          │          │          │
├─────────────┼──────────────┼──────────────┼──────┼──────┼────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 15/01/2024  │ Bucks        │ 76ers        │ 222  │ 230  │ 4/6    │ OVER     │ AWAY_TEAM│ MEDIUM   │ +8.1     │ BUC_006  │
│ (23:30)     │              │              │      │      │        │          │          │          │          │          │
├─────────────┼──────────────┼──────────────┼──────┼──────┼────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 15/01/2024  │ Mavericks    │ Rockets      │ 210  │ 212  │ 3/6    │ NO_BET   │ HOME_TEAM│ LOW      │ +2.4     │ MAV_007  │
│ (01:00)     │              │              │      │      │        │          │          │          │          │          │
├─────────────┼──────────────┼──────────────┼──────┼──────┼────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ 15/01/2024  │ Trail Blazers│ Thunder      │ 208  │ 194  │ 5/6    │ UNDER    │ AWAY_TEAM│ HIGH     │ -13.8    │ TRA_008  │
│ (03:30)     │              │              │      │      │        │          │          │          │          │          │
└─────────────┴──────────────┴──────────────┴──────┴──────┴────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

---

## Color Coding Legend

### Prediction Colors:
- **🟢 OVER** - Green (strong over signal)
- **🔴 UNDER** - Red (strong under signal)  
- **🟡 NO_BET** - Yellow (weak signals)

### Winner Colors:
- **🟢 HOME_TEAM** - Green (home team predicted to win)
- **🔴 AWAY_TEAM** - Red (away team predicted to win)
- **🟡 NO_BET** - Yellow (no clear winner prediction)

### Confidence Colors:
- **🟢 HIGH** - Bright Green (strong signals + winning patterns)
- **🟡 MEDIUM** - Yellow (good signals with one weakness)
- **🔴 LOW** - Red (weak or extreme signals)

---

## Example Analysis

### Row 1: Lakers vs Warriors
- **Prediction**: OVER 225
- **Winner**: HOME_TEAM (Lakers)
- **Confidence**: HIGH
- **Line**: 225, **AVG**: 237, **RATIO**: 5/6, **AvgRate**: +12.5
- **Analysis**: 5 out of 6 H2H matches went OVER, strong historical pattern

### Row 2: Celtics vs Heat  
- **Prediction**: UNDER 218
- **Winner**: AWAY_TEAM (Heat)
- **Confidence**: HIGH
- **Line**: 218, **AVG**: 207, **RATIO**: 4/6, **AvgRate**: -11.2
- **Analysis**: 4 out of 6 H2H matches went UNDER, consistent under pattern

### Row 3: Bulls vs Nets
- **Prediction**: NO_BET
- **Winner**: NO_BET
- **Confidence**: LOW
- **Line**: 212, **AVG**: 216, **RATIO**: 3/6, **AvgRate**: +3.8
- **Analysis**: Only 3 out of 6 H2H matches went OVER, mixed pattern

### Row 4: Suns vs Clippers
- **Prediction**: OVER 220
- **Winner**: HOME_TEAM (Suns)
- **Confidence**: MEDIUM
- **Line**: 220, **AVG**: 229, **RATIO**: 4/6, **AvgRate**: +9.3
- **Analysis**: 4 out of 6 H2H matches went OVER, good over pattern

### Row 5: Nuggets vs Jazz
- **Prediction**: UNDER 215
- **Winner**: NO_BET
- **Confidence**: LOW
- **Line**: 215, **AVG**: 196, **RATIO**: 5/6, **AvgRate**: -18.7
- **Analysis**: 5 out of 6 H2H matches went UNDER, but rate too extreme

---

## Confidence Logic Examples

### HIGH Confidence Cases:
1. **OVER + HIGH**: Rate 7-15 + winning streak ≥3 + ≥4 H2H wins
2. **UNDER + HIGH**: Rate -7 to -15 + winning streak ≥3 + ≥4 H2H wins
3. **Team Winner + HIGH**: ≥4 H2H wins + winning streak ≥3

### MEDIUM Confidence Cases:
1. **OVER + MEDIUM**: Rate 7-15 but missing streak or H2H wins
2. **UNDER + MEDIUM**: Rate -7 to -15 but missing streak or H2H wins
3. **Team Winner + MEDIUM**: ≥4 H2H wins but winning streak < 3

### LOW Confidence Cases:
1. **OVER + LOW**: Rate 16-20 (too extreme)
2. **UNDER + LOW**: Rate -16 to -20 (too extreme)
3. **NO_BET + LOW**: Rate -6 to +6 (weak signals)

---

## Table Features

### **Columns:**
- **Date/Time**: Match date and time (15/01/2024 (14:00) format)
- **Home**: Home team name
- **Away**: Away team name  
- **Line**: Bookmaker total line
- **AVG**: Average H2H total score (calculated from historical matches)
- **RATIO**: Ratio of times teams went over/under in H2H matches (e.g., 5/6 for OVER, 4/6 for UNDER)
- **Prediction**: OVER/UNDER/NO_BET
- **Winner**: HOME_TEAM/AWAY_TEAM/NO_BET
- **Confidence**: HIGH/MEDIUM/LOW
- **AvgRate**: Average rate value (formatted to 1 decimal)
- **Match ID**: Unique match identifier

### **Filtering Options:**
- Filter by prediction type (OVER/UNDER/NO_BET)
- Filter by confidence level (HIGH/MEDIUM/LOW)
- Filter by team winner prediction
- Filter by league or team
- Sort by confidence, rate, or date

### **Interactive Features:**
- Click on any row to see detailed analysis
- Export results to CSV/JSON
- Save favorite predictions
- Track prediction accuracy over time

---

## Implementation Notes

This table is generated by the enhanced ScoreWise algorithm that:

1. **Analyzes H2H Patterns**: Counts wins/losses between teams
2. **Calculates Rate Values**: Difference between H2H totals and bookmaker line
3. **Considers Winning Streaks**: Recent form analysis
4. **Applies Rate Thresholds**: Precise ranges for different predictions
5. **Determines Confidence**: Based on signal strength and patterns
6. **Predicts Team Winners**: Based on H2H dominance and streaks

The table provides a comprehensive view of all prediction aspects in an easy-to-read format with clear color coding for quick decision making. 