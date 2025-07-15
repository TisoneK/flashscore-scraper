# Prediction Table Example

This document shows the format and structure of the prediction results table displayed in the CLI.

## Table Structure

The prediction system now displays results in **two separate tables** for better clarity:

### 1. Actionable Predictions Table (OVER/UNDER)
- **Purpose**: Shows predictions you can act on immediately
- **Color**: Green header with green/red prediction colors
- **Contains**: Only OVER and UNDER predictions

---

### 🎯 ACTIONABLE PREDICTIONS (HOME/AWAY)
Shows only matches qualifying for a win bet (≥4/6 and 3-game streak). Displays the H2H win ratio (RATIO), current streak, and odds for the prediction. This table is based solely on H2H win ratio and winning streak, not on average rate or bookmaker line.

```
🎯 ACTIONABLE PREDICTIONS (HOME/AWAY)
┌─────┬──────────┬──────────────┬─────────────────┬──────────────┬──────────────┬───────┬───────┬───────┬---------┬---------┐
│ NO. │ MATCH_ID │ DATE/TIME    │ COUNTRY/LEAGUE  │ HOME         │ AWAY         │ RATIO │ CONF. │ PRED. │ RESULTS │ STATUS  │
├─────┼──────────┼──────────────┼─────────────────┼──────────────┼──────────────┼───────┼───────┼───────┼---------┼---------┤
│  1  │ 12345682 │ 16.01.2025   │ Spain/La Liga   │ Real Madrid  │ Barcelona    │ 5/6   │ HIGH  │ HOME  │  Won    │ Settled │
│  2  │ 12345683 │ 16.01.2025   │ Italy/Serie A   │ Juventus     │ Inter Milan  │ 4/6   │ MED   │ AWAY  │ Pending │ Pending │
└─────┴──────────┴──────────────┴─────────────────┴──────────────┴──────────────┴───────┴───────┴───────┴---------┴---------┘

📊 Found 2 actionable home/away predictions
```

**Notes:**
- Only matches with at least 4 wins in the last 6 and a 3-game winning streak are shown.
- **RATIO**: H2H win ratio for the predicted team (e.g., 4/6, 5/6).
- **CONF.**: Confidence level, based on streaks and H2H wins (HIGH, MED, LOW).
- **PRED.**: The team predicted to win (HOME or AWAY).
- "RESULTS" and "STATUS" columns track the outcome and settlement status.
- Team names with more than two words wrap to two lines.
- This table does NOT use average rate, bookmaker line, or over/under logic.
- 'NO_BET' is used instead of 'NO_WINNER_PREDICTION' where appropriate.

---

### ⏸️ NO_BET PREDICTIONS (For Team Winner Analysis)
(These are matches that do not qualify for actionable home/away or over/under predictions, but may have a team winner suggestion.)

```
⏸️  NO_BET PREDICTIONS (For Team Winner Analysis)
┌─────┬──────────┬─────────────────┬─────────────────┬──────────────┬──────────────┬──────┬─────┬──────┬──────┬──────────┬──────┬─────────┐
│ NO. │ MATCH_ID │   DATE/TIME     │ COUNTRY/LEAGUE │     HOME     │     AWAY     │ LINE │ AVG │RATIO │ PRED.│  WINNER  │ CONF.│ AVGRATE │
├─────┼──────────┼─────────────────┼─────────────────┼──────────────┼──────────────┼──────┼─────┼──────┼──────┼──────────┼──────┼─────────┤
│  1  │ 12345680 │ 15.01.2025     │ England         │ Manchester   │ Liverpool    │182.5 │181.8│ 2/4  │NO_BET│HOME      │ HIGH │ +2.15   │
│     │          │    (19:00)      │ Premier League  │ United       │              │      │     │      │      │          │      │         │
├─────┼──────────┼─────────────────┼─────────────────┼──────────────┼──────────────┼──────┼─────┼──────┼──────┼──────────┼──────┼─────────┤
│  2  │ 12345681 │ 15.01.2025     │ Germany         │ Bayern       │ Dortmund     │175.0 │174.5│ 3/5  │NO_BET│AWAY      │MEDIUM│ +1.25   │
│     │          │    (20:15)      │ Bundesliga      │ Munich       │              │      │     │      │      │          │      │         │
└─────┴──────────┴─────────────────┴─────────────────┴──────────────┴──────────────┴──────┴─────┴──────┴──────┴──────────┴──────┴─────────┘

📊 Found 2 NO_BET predictions (check team winners)
```

## Table Format

Both tables use the same column structure but with different styling:

| Column | Description | Example | Color |
|--------|-------------|---------|-------|
| NO. | Row number | 1, 2, 3... | Cyan |
| MATCH_ID | Unique match identifier | 12345678 | Cyan |
| DATE/TIME | Match date and time | 15.01.2025 (20:30) | Cyan |
| COUNTRY/LEAGUE | Country and league name | Spain<br>La Liga | White |
| HOME | Home team name | Real Madrid | White |
| AWAY | Away team name | Barcelona | White |
| LINE | Bookmaker total line | 185.5 | Yellow |
| AVG | Average H2H total | 182.3 | Green |
| RATIO | Over/Under ratio | 3/5 | Blue |
| PRED. | Prediction recommendation | OVER/UNDER/NO_BET | Green/Red/Yellow |
| WINNER | Team winner prediction | HOME_TEAM/AWAY_TEAM/NO_BET | Green/Red/Yellow |
| CONF. | Confidence level | HIGH/MEDIUM/LOW | Bright Green/Yellow/Red |
| AVGRATE | Average rate calculation | +12.45 | Green |

## Example Display

### Actionable Predictions Table
```
🎯 ACTIONABLE PREDICTIONS (OVER/UNDER)
┌─────┬──────────┬─────────────────┬─────────────────┬──────────────┬──────────────┬──────┬─────┬──────┬──────┬──────────┬──────┬─────────┐
│ NO. │ MATCH_ID │   DATE/TIME     │ COUNTRY/LEAGUE │     HOME     │     AWAY     │ LINE │ AVG │RATIO │ PRED.│  WINNER  │ CONF.│ AVGRATE │
├─────┼──────────┼─────────────────┼─────────────────┼──────────────┼──────────────┼──────┼─────┼──────┼──────┼──────────┼──────┼─────────┤
│  1  │ 12345678 │ 15.01.2025     │ Spain           │ Real Madrid  │ Barcelona    │185.5 │182.3│ 3/5  │ OVER │HOME_TEAM │ HIGH │ +12.45  │
│     │          │    (20:30)      │ La Liga         │              │              │      │     │      │      │          │      │         │
├─────┼──────────┼─────────────────┼─────────────────┼──────────────┼──────────────┼──────┼─────┼──────┼──────┼──────────┼──────┼─────────┤
│  2  │ 12345679 │ 15.01.2025     │ Italy           │ Juventus     │ Inter Milan  │178.0 │185.2│ 4/6  │UNDER │AWAY_TEAM │MEDIUM│ -8.75   │
│     │          │    (21:45)      │ Serie A         │              │              │      │     │      │      │          │      │         │
└─────┴──────────┴─────────────────┴─────────────────┴──────────────┴──────────────┴──────┴─────┴──────┴──────┴──────────┴──────┴─────────┘

📊 Found 2 actionable predictions
```

### Home/Away Predictions Table
```
⏸️  NO_BET PREDICTIONS (For Team Winner Analysis)
┌─────┬──────────┬─────────────────┬─────────────────┬──────────────┬──────────────┬──────┬─────┬──────┬──────┬──────────┬──────┬─────────┐
│ NO. │ MATCH_ID │   DATE/TIME     │ COUNTRY/LEAGUE │     HOME     │     AWAY     │ LINE │ AVG │RATIO │ PRED.│  WINNER  │ CONF.│ AVGRATE │
├─────┼──────────┼─────────────────┼─────────────────┼──────────────┼──────────────┼──────┼─────┼──────┼──────┼──────────┼──────┼─────────┤
│  1  │ 12345680 │ 15.01.2025     │ England         │ Manchester   │ Liverpool    │182.5 │181.8│ 2/4  │NO_BET│HOME_TEAM │ HIGH │ +2.15   │
│     │          │    (19:00)      │ Premier League  │ United       │              │      │     │      │      │          │      │         │
├─────┼──────────┼─────────────────┼─────────────────┼──────────────┼──────────────┼──────┼─────┼──────┼──────┼──────────┼──────┼─────────┤
│  2  │ 12345681 │ 15.01.2025     │ Germany         │ Bayern       │ Dortmund     │175.0 │174.5│ 3/5  │NO_BET│AWAY_TEAM │MEDIUM│ +1.25   │
│     │          │    (20:15)      │ Bundesliga      │ Munich       │              │      │     │      │      │          │      │         │
└─────┴──────────┴─────────────────┴─────────────────┴──────────────┴──────────────┴──────┴─────┴──────┴──────┴──────────┴──────┴─────────┘

📊 Found 2 NO_BET predictions (check team winners)
```

### Summary
```
📈 SUMMARY: 2/4 predictions are actionable (50.0%)
```

## Benefits of Dual-Table System

1. **Clear Separation**: Actionable predictions are immediately visible
2. **Reduced Clutter**: NO_BET games don't crowd the actionable table
3. **Team Winner Focus**: NO_BET table highlights team winner predictions
4. **Better Decision Making**: Users can quickly identify what to bet on
5. **Improved UX**: Less overwhelming display with logical grouping

## Color Coding

### Actionable Predictions Table
- **Header**: Bold green with 🎯 emoji
- **OVER predictions**: Green text
- **UNDER predictions**: Red text
- **High confidence**: Bright green
- **Medium confidence**: Yellow
- **Low confidence**: Red

### NO_BET Predictions Table
- **Header**: Bold yellow with ⏸️ emoji
- **NO_BET predictions**: Yellow text
- **Team winners**: Green (HOME_TEAM) / Red (AWAY_TEAM)
- **Same confidence colors**: Bright green/Yellow/Red

## Usage Notes

- **Actionable Table**: Focus on these predictions for immediate betting decisions
- **NO_BET Table**: Check team winner predictions for alternative betting opportunities
- **Summary**: Shows percentage of actionable predictions for quick assessment
- **Filtering**: Both tables maintain separate filtering and sorting capabilities
- **Export**: Can export both tables separately or combined

## Console Clearing Strategy

The CLI implements a strategic console clearing approach to maintain clean, uncluttered output:

### When Console is Cleared:
- ✅ **Initial prediction display** - Clean start when showing prediction results
- ✅ **After filtering** - Clear display before showing filtered results
- ✅ **After sorting** - Clear display before showing sorted results
- ✅ **Navigation between menus** - Clean transitions between different sections

### When Console is NOT Cleared:
- ❌ **During prediction details** - Details are shown in context with the table
- ❌ **After export operations** - Export messages appear below current content
- ❌ **Error messages** - Errors are shown without clearing to maintain context
- ❌ **User input prompts** - Prompts appear without clearing to maintain flow

### Header Display:
- **Always shown after clearing** - Appropriate headers are displayed after each console clear
- **Context-aware headers** - Different headers for different sections (prediction, settings, etc.)
- **Consistent styling** - Headers use consistent color scheme and formatting

### Benefits:
1. **Clean transitions** - Smooth navigation between different sections
2. **Context preservation** - Important information remains visible when needed
3. **User-friendly flow** - Natural progression through the interface
4. **Reduced clutter** - No unnecessary clearing that disrupts user experience 