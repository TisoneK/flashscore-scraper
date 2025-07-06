#!/usr/bin/env python3
"""
Test runner for WebAutoPy project
"""

import sys
import os
import unittest
import argparse

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def run_all_tests():
    """Run all tests in the tests directory"""
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_specific_test(test_module):
    """Run a specific test module"""
    try:
        # Import the test module
        module_name = f'tests.{test_module}'
        test_module = __import__(module_name, fromlist=[''])
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    except ImportError as e:
        print(f"Error: Could not import test module '{test_module}': {e}")
        return False


def list_available_tests():
    """List all available test modules"""
    test_dir = os.path.dirname(__file__)
    test_files = [f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.py')]
    
    print("Available test modules:")
    for test_file in sorted(test_files):
        module_name = test_file[:-3]  # Remove .py extension
        print(f"  - {module_name}")
    
    print(f"\nTotal: {len(test_files)} test modules")
    
    # Group tests by category
    print("\nTest Categories:")
    print("  📊 Data Models:")
    print("    - test_models")
    print("    - test_elements_model")
    print("  🔄 Data Loaders:")
    print("    - test_data_loaders")
    print("  📈 Data Extractors:")
    print("    - test_odds_data_extractor")
    print("    - test_data_extractors")
    print("  ✅ Data Verifiers:")
    print("    - test_data_verifiers")
    print("  🕷️  Scraper:")
    print("    - test_scraper")


def run_test_category(category):
    """Run tests for a specific category"""
    categories = {
        'models': ['test_models', 'test_elements_model'],
        'loaders': ['test_data_loaders'],
        'extractors': ['test_odds_data_extractor', 'test_data_extractors'],
        'verifiers': ['test_data_verifiers'],
        'scraper': ['test_scraper'],
        'all': None  # Will run all tests
    }
    
    if category not in categories:
        print(f"Error: Unknown category '{category}'")
        print("Available categories:", list(categories.keys()))
        return False
    
    if category == 'all':
        return run_all_tests()
    
    success = True
    for test_module in categories[category]:
        print(f"\nRunning {test_module}...")
        if not run_specific_test(test_module):
            success = False
    
    return success


def main():
    """Main function to run tests"""
    parser = argparse.ArgumentParser(description='Run WebAutoPy tests')
    parser.add_argument('--module', '-m', help='Run specific test module (e.g., test_odds_data_extractor)')
    parser.add_argument('--category', '-c', help='Run tests for specific category (models, loaders, extractors, verifiers, scraper, all)')
    parser.add_argument('--list', '-l', action='store_true', help='List all available test modules')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.list:
        list_available_tests()
        return
    
    if args.category:
        print(f"Running tests for category: {args.category}")
        success = run_test_category(args.category)
    elif args.module:
        print(f"Running test module: {args.module}")
        success = run_specific_test(args.module)
    else:
        print("Running all tests...")
        success = run_all_tests()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main() 