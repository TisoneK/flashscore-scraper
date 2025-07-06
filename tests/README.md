# WebAutoPy Tests

This directory contains comprehensive tests for the WebAutoPy project, covering all components in the `/data` directory and beyond.

## Test Structure

### 📊 Data Models
- `test_models.py` - Tests for data models (MatchModel, OddsModel, H2HMatchModel)
- `test_elements_model.py` - Tests for elements_model.py dataclasses

### 🔄 Data Loaders
- `test_data_loaders.py` - Tests for all data loaders (MatchDataLoader, OddsDataLoader, H2HDataLoader)

### 📈 Data Extractors
- `test_odds_data_extractor.py` - Tests for the OddsDataExtractor class and odds selection logic
- `test_data_extractors.py` - Tests for MatchDataExtractor and H2HDataExtractor

### ✅ Data Verifiers
- `test_data_verifiers.py` - Tests for all verifier classes (BaseVerifier, MatchDataVerifier, OddsDataVerifier, H2HDataVerifier, ModelVerifier, LoaderVerifier, ExtractorVerifier)

### 🕷️ Scraper
- `test_scraper.py` - Tests for the main FlashscoreScraper functionality

### 🚀 Test Runner
- `run_tests.py` - Flexible test runner with command-line options

## Running Tests

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Tests by Category
```bash
# Run all data model tests
python tests/run_tests.py --category models

# Run all data loader tests
python tests/run_tests.py --category loaders

# Run all data extractor tests
python tests/run_tests.py --category extractors

# Run all data verifier tests
python tests/run_tests.py --category verifiers

# Run all scraper tests
python tests/run_tests.py --category scraper

# Run all tests (same as no arguments)
python tests/run_tests.py --category all
```

### Run Specific Test Module
```bash
python tests/run_tests.py --module test_odds_data_extractor
python tests/run_tests.py --module test_models
python tests/run_tests.py --module test_data_loaders
python tests/run_tests.py --module test_data_extractors
python tests/run_tests.py --module test_data_verifiers
python tests/run_tests.py --module test_elements_model
python tests/run_tests.py --module test_scraper
```

### List Available Test Modules
```bash
python tests/run_tests.py --list
```

### Run Individual Test Files
```bash
python -m unittest tests.test_odds_data_extractor
python -m unittest tests.test_models
python -m unittest tests.test_data_loaders
python -m unittest tests.test_data_extractors
python -m unittest tests.test_data_verifiers
python -m unittest tests.test_elements_model
python -m unittest tests.test_scraper
```

## Test Coverage

### 📊 Data Models Tests
- **MatchModel**: Creation, validation, data type handling, dictionary conversion, automatic timestamp generation
- **OddsModel**: Creation with/without values, property access, data validation
- **H2HMatchModel**: Creation, data extraction, competition field handling
- **ElementsModel**: Dataclass creation, default values, partial initialization, modification

### 🔄 Data Loaders Tests
- **MatchDataLoader**: Initialization, main page loading, match ID extraction, match loading, element extraction
- **OddsDataLoader**: Initialization, home/away odds loading, over/under odds loading, element extraction
- **H2HDataLoader**: Initialization, H2H data loading, element extraction, row counting

### 📈 Data Extractors Tests
- **OddsDataExtractor**: 
  - `has_half_point()` method validation
  - `get_selected_alternative()` with .5 alternatives
  - `get_selected_alternative()` without .5 alternatives (fallback)
  - `get_selected_alternative()` with low odds
  - `get_best_alternative()` priority logic
  - Property getters and setters
  - Data extraction methods
- **MatchDataExtractor**: Match data extraction, property access, exception handling
- **H2HDataExtractor**: H2H data extraction, individual field access, row indexing

### ✅ Data Verifiers Tests
- **BaseVerifier**: Abstract base class functionality
- **MatchDataVerifier**: Match page verification, match data validation
- **OddsDataVerifier**: Odds validation (match_total, over_odds, under_odds, home_odds, away_odds)
- **H2HDataVerifier**: H2H section verification, H2H data validation
- **ModelVerifier**: Model validation, required field checking
- **LoaderVerifier**: Loader validation, driver and elements checking
- **ExtractorVerifier**: Extractor validation, loader and elements checking

### 🕷️ Scraper Tests
- Initialization and setup
- Data loading methods
- Odds validation logic
- Skip reason composition
- Match data extraction
- H2H data extraction
- Logging functionality

## Key Testing Features

### Mock Objects
Tests use comprehensive mocking to avoid external dependencies:
- `MockOddsLoader` - Simulates odds data loader
- `MockOddsElements` - Simulates web elements
- `MockElement` - Simulates individual web elements
- `MockDriver` - Simulates web driver
- `MockSeleniumUtils` - Simulates Selenium utilities

### Edge Cases
Tests cover various edge cases:
- Missing or invalid data
- Low odds scenarios
- No .5 alternatives
- Empty or null values
- Invalid indices
- Network timeouts
- Element not found scenarios

### Priority Logic Testing
The odds selection logic is thoroughly tested:
1. First priority: Over odds closest to 1.85 among alternatives with .5
2. Second priority: Over odds closest to 1.85 among all alternatives (fallback)
3. Always returns the best available alternative, never None

### Data Validation Testing
Comprehensive validation testing for:
- Odds format validation (numeric ranges, decimal places)
- Match data completeness
- H2H data integrity
- Model field requirements

## Adding New Tests

When adding new functionality, create corresponding tests:

1. Create a new test file: `test_<module_name>.py`
2. Follow the existing naming convention: `Test<ClassName>`
3. Use descriptive test method names: `test_<method_name>_<scenario>`
4. Include both positive and negative test cases
5. Mock external dependencies appropriately
6. Add the new test to the appropriate category in `run_tests.py`

## Example Test Structure

```python
class TestNewFeature(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        pass
    
    def test_feature_normal_case(self):
        """Test normal operation"""
        pass
    
    def test_feature_edge_case(self):
        """Test edge case handling"""
        pass
    
    def test_feature_error_handling(self):
        """Test error handling"""
        pass
```

## Test Categories

The test runner supports running tests by category:

- **models**: Data model tests
- **loaders**: Data loader tests  
- **extractors**: Data extractor tests
- **verifiers**: Data verifier tests
- **scraper**: Main scraper tests
- **all**: All tests

## Continuous Integration

These tests can be integrated into CI/CD pipelines to ensure code quality and prevent regressions. The comprehensive coverage ensures that all data processing components are thoroughly tested.

## Test Statistics

- **Total Test Files**: 7
- **Test Categories**: 5
- **Coverage**: All `/data` directory components
- **Mock Objects**: 5+ different mock types
- **Edge Cases**: 20+ different scenarios 