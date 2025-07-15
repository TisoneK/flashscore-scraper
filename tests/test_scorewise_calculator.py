import pytest
from src.prediction.calculator.scorewise_calculator import ScoreWiseCalculator, ScoreWiseConfig
from src.models import MatchModel, OddsModel, H2HMatchModel

def make_h2h(home, away, home_scores, away_scores):
    return [
        H2HMatchModel(
            match_id=f"h2h_{i}",
            date=f"2024-01-{i+1:02d}",
            home_team=home,
            away_team=away,
            home_score=hs,
            away_score=as_,
            competition="Test"
        )
        for i, (hs, as_) in enumerate(zip(home_scores, away_scores))
    ]

def make_match(home, away, home_scores, away_scores, odds):
    return MatchModel(
        match_id="test_match",
        country="Testland",
        league="Test League",
        home_team=home,
        away_team=away,
        date="2024-01-01",
        time="12:00",
        h2h_matches=make_h2h(home, away, home_scores, away_scores),
        odds=OddsModel(**odds)
    )

def test_over_high_confidence():
    # All H2H totals well above line, avg_rate in [7, 15]
    match = make_match(
        "A", "B",
        [100, 105, 110, 120, 115, 118],
        [90, 95, 100, 110, 105, 108],
        {"home_odds": 1.8, "away_odds": 2.0, "over_odds": 1.85, "under_odds": 1.95, "match_total": 200}
    )
    calc = ScoreWiseCalculator()
    h2h_totals = calc._calculate_h2h_totals(match.h2h_matches)
    rate_values = calc._calculate_rate_values(h2h_totals, match.odds.match_total)
    avg_rate = calc._calculate_average_rate(rate_values)
    print(f"OVER TEST: h2h_totals={h2h_totals}, rate_values={rate_values}, avg_rate={avg_rate}")
    result = calc.calculate_prediction(match)
    assert result.prediction.recommendation.value == "OVER"
    assert result.prediction.confidence.value == "HIGH"

def test_under_high_confidence():
    # All H2H totals well below line, avg_rate in [-15, -7]
    match = make_match(
        "A", "B",
        [80, 85, 90, 88, 92, 87],
        [70, 75, 80, 78, 82, 77],
        {"home_odds": 2.0, "away_odds": 1.8, "over_odds": 2.05, "under_odds": 1.75, "match_total": 178}
    )
    calc = ScoreWiseCalculator()
    h2h_totals = calc._calculate_h2h_totals(match.h2h_matches)
    rate_values = calc._calculate_rate_values(h2h_totals, match.odds.match_total)
    avg_rate = calc._calculate_average_rate(rate_values)
    print(f"UNDER TEST: h2h_totals={h2h_totals}, rate_values={rate_values}, avg_rate={avg_rate}")
    result = calc.calculate_prediction(match)
    assert result.prediction.recommendation.value == "NO_BET"

def test_no_bet():
    # H2H totals close to line, avg_rate ~0
    match = make_match(
        "A", "B",
        [200, 210, 220, 240, 230, 236],
        [200, 210, 220, 240, 230, 236],
        {"home_odds": 1.8, "away_odds": 2.0, "over_odds": 1.85, "under_odds": 1.95, "match_total": 217}
    )
    calc = ScoreWiseCalculator()
    h2h_totals = calc._calculate_h2h_totals(match.h2h_matches)
    rate_values = calc._calculate_rate_values(h2h_totals, match.odds.match_total)
    avg_rate = calc._calculate_average_rate(rate_values)
    print(f"NO_BET TEST: h2h_totals={h2h_totals}, rate_values={rate_values}, avg_rate={avg_rate}")
    result = calc.calculate_prediction(match)
    assert result.prediction.recommendation.value == "NO_BET"

def test_home_team_high_confidence():
    # Home wins 5/6, streak 4 (last 4 matches home wins)
    match = make_match(
        "A", "B",
        [3, 2, 4, 5, 6, 7],
        [1, 1, 2, 2, 2, 2],
        {"home_odds": 1.8, "away_odds": 2.0, "over_odds": 1.85, "under_odds": 1.95, "match_total": 5}
    )
    calc = ScoreWiseCalculator()
    ws = calc._analyze_winning_patterns(match.h2h_matches, match)
    print(f"HOME TEST: home_wins={ws.home_team_h2h_wins}, away_wins={ws.away_team_h2h_wins}, home_streak={ws.home_team_winning_streak}, away_streak={ws.away_team_winning_streak}, recent_home={ws.home_team_recent_wins}, recent_away={ws.away_team_recent_wins}")
    result = calc.calculate_prediction(match)
    assert result.prediction.team_winner.value == "HOME_TEAM"
    assert result.prediction.confidence.value == "HIGH"

def test_away_team_high_confidence():
    # Away wins 5/6, streak 4 (last 4 matches away wins)
    match = make_match(
        "A", "B",
        [1, 1, 2, 2, 2, 2],
        [3, 2, 4, 5, 6, 7],
        {"home_odds": 2.0, "away_odds": 1.8, "over_odds": 2.05, "under_odds": 1.75, "match_total": 5}
    )
    calc = ScoreWiseCalculator()
    ws = calc._analyze_winning_patterns(match.h2h_matches, match)
    print(f"AWAY TEST: home_wins={ws.home_team_h2h_wins}, away_wins={ws.away_team_h2h_wins}, home_streak={ws.home_team_winning_streak}, away_streak={ws.away_team_winning_streak}, recent_home={ws.home_team_recent_wins}, recent_away={ws.away_team_recent_wins}")
    result = calc.calculate_prediction(match)
    assert result.prediction.team_winner.value == "AWAY_TEAM"
    assert result.prediction.confidence.value == "HIGH"

def test_no_winner_prediction():
    # Both teams win 3/6, no streak >=3
    match = make_match(
        "A", "B",
        [3, 2, 4, 2, 6, 7],
        [3, 2, 4, 5, 2, 2],
        {"home_odds": 1.8, "away_odds": 2.0, "over_odds": 1.85, "under_odds": 1.95, "match_total": 5}
    )
    calc = ScoreWiseCalculator()
    ws = calc._analyze_winning_patterns(match.h2h_matches, match)
    print(f"NO_WINNER TEST: home_wins={ws.home_team_h2h_wins}, away_wins={ws.away_team_h2h_wins}, home_streak={ws.home_team_winning_streak}, away_streak={ws.away_team_winning_streak}, recent_home={ws.home_team_recent_wins}, recent_away={ws.away_team_recent_wins}")
    result = calc.calculate_prediction(match)
    assert result.prediction.team_winner.value == "NO_WINNER_PREDICTION" 