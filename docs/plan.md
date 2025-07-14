Installation has a flow
- How it works now:

### Installation
1. **Clone and install:** installs in the system environment
```bash
git clone https://github.com/TisoneK/flashscore-scraper.git
cd flashscore-scraper
pip install -e .
```

2. **Set up drivers:** creates our virtual env and required files and folders
```bash
fss --init
```

3. **Start scraping view prediction:**
```bash
fss -u    # Launch GUI
# or
fss -c    # Launch CLI (recommended)
```

- We have installed in the system but we also created ```.venv```
- For users it will be okay to just use the system's intallation since it's ideal but for the developer it will be a waste of resources since they will have to activate the .venv and run again ```pip install -e .```
- We need to come up with a user friendly installation

-------------------------------------------------------------

Prediction Table
- Add RESULTS column after AVGRATE column
- Add STATUS after RESULTS column (Pending..., Won, Lost)
- All table contents displays without concatination
- Content wrapping. If a team has more than two words in the team name we need to wrap them in two lines
- Instead of "NO_WINNER_PREDICTION" we need to put "NO_BET"
- For the winner column; instead of "HOME_TEAM" or "AWAY_TEAM", we need to output "HOME" or "AWAY"
- In prediction, the odds for the prediction will appear below the prediction
    e.g: 
    OVER
    @1.85

    HOME
    @2.11

- We will have two tables
    + 🎯 ACTIONABLE PREDICTIONS (OVER/UNDER)
        - This will solely focus on over/under prediction
        - No information about home/away win
        - Over/Under ratio
    + 🎯 ACTIONABLE PREDICTIONS (HOME/AWAY)
        - Specifically focuses on the matches that qualifies for win bet
        - The rule/algorith should be strictly >= 4 out 6 and winning streak for the most recent 3 games
        - Home/Away ratio
- A match can appear in both tables if it qualifies in both tables
- Matches that do not qualify in any of the tables over/under and home/away should not appear anywhere
- A user can update the results of a match on the console using match id or by selecting table type and entering the number of match in the table eg match 1 e.t.c




--------------------------------------------------------

- View Details/Export is not functional

--------------------------------------------------------

Scraper
--------------------------------------------------------
- Currently we are only fetching matches which are complete; we need to fetch all scheduled games's data even if they are incomplete
- Matches with all the required data will have status COMPLETE while those without all required data will have status INCOMPLETE
- Scraped data will be stored in a database
- Matches with status COMPLETE will be used for prediction generation


Results Data Scraping (The next day)
------------------------------------------------------
-Update Match Model to have scores
    - home_scores
    - away_scores

- Create new data loader in @data module for loading results page
- Create new data extractor in @data module for exctracting results
    - Q1 -> First quarter results (home, away)
    - Q2 -> Second quarter results (home, away)
    - Q3 -> Third quarter results (home, away)
    - Q4 -> Fourth quarter results (home, away)

    - First Half Results -> Q1 + Q2
    - Second Half Results -> Q3 + Q4

    - Fulltime Results
