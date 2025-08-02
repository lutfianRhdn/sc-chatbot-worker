#!/usr/bin/env python3
"""
Test runner for sc-chatbot-worker comprehensive unit tests.

This script runs all unit tests for supervisor and worker classes,
providing detailed coverage and results reporting.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Verbose output
    python run_tests.py --pattern    # Run specific test pattern
    python run_tests.py --coverage   # Run with coverage report
"""

import unittest
import sys
import os
import argparse
from io import StringIO


def discover_tests(test_dir, pattern='test*.py'):
    """Discover all test modules in the test directory."""
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern=pattern)
    return suite


def run_test_suite(suite, verbosity=1):
    """Run the test suite and return results."""
    stream = StringIO()
    runner = unittest.TextTestRunner(
        stream=stream,
        verbosity=verbosity,
        buffer=True,
        failfast=False
    )
    
    result = runner.run(suite)
    
    # Print results to stdout
    print(stream.getvalue())
    
    return result


def print_test_summary(result):
    """Print a comprehensive test summary."""
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    success = total_tests - failures - errors - skipped
    
    print(f"Total Tests Run: {total_tests}")
    print(f"Successful:      {success}")
    print(f"Failures:        {failures}")
    print(f"Errors:          {errors}")
    print(f"Skipped:         {skipped}")
    
    if total_tests > 0:
        success_rate = (success / total_tests) * 100
        print(f"Success Rate:    {success_rate:.1f}%")
    
    print("="*70)
    
    # Print detailed failure information
    if result.failures:
        print("\nFAILURES:")
        print("-" * 50)
        for test, traceback in result.failures:
            print(f"FAIL: {test}")
            print(traceback)
            print("-" * 50)
    
    if result.errors:
        print("\nERRORS:")
        print("-" * 50)
        for test, traceback in result.errors:
            print(f"ERROR: {test}")
            print(traceback)
            print("-" * 50)
    
    return result.wasSuccessful()


def run_with_coverage():
    """Run tests with coverage analysis if coverage.py is available."""
    try:
        import coverage
        
        # Start coverage
        cov = coverage.Coverage(source=['src'])
        cov.start()
        
        # Run tests
        test_dir = os.path.join(os.path.dirname(__file__), 'tests')
        suite = discover_tests(test_dir)
        result = run_test_suite(suite, verbosity=2)
        
        # Stop coverage and generate report
        cov.stop()
        cov.save()
        
        print("\n" + "="*70)
        print("COVERAGE REPORT")
        print("="*70)
        cov.report()
        
        # Generate HTML report
        try:
            cov.html_report(directory='htmlcov')
            print("\nHTML coverage report generated in 'htmlcov' directory")
        except Exception as e:
            print(f"Could not generate HTML report: {e}")
        
        return print_test_summary(result)
        
    except ImportError:
        print("Coverage.py not installed. Install with: pip install coverage")
        print("Running tests without coverage...")
        return run_without_coverage()


def run_without_coverage(verbosity=1, pattern='test*.py'):
    """Run tests without coverage analysis."""
    # Get the tests directory
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    
    if not os.path.exists(test_dir):
        print(f"Test directory not found: {test_dir}")
        return False
    
    print(f"Discovering tests in: {test_dir}")
    print(f"Test pattern: {pattern}")
    print("="*70)
    
    # Discover and run tests
    suite = discover_tests(test_dir, pattern)
    result = run_test_suite(suite, verbosity)
    
    return print_test_summary(result)


def list_available_tests():
    """List all available test modules and classes."""
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    
    print("AVAILABLE TESTS:")
    print("="*50)
    
    for root, dirs, files in os.walk(test_dir):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.startswith('test') and file.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, file), test_dir)
                module_name = rel_path.replace(os.sep, '.').replace('.py', '')
                print(f"  {module_name}")
    
    print("="*50)


def validate_test_structure():
    """Validate that test files are properly structured."""
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    issues = []
    
    print("VALIDATING TEST STRUCTURE:")
    print("="*50)
    
    # Check if main test files exist
    expected_files = [
        'test_supervisor.py',
        'test_worker_base.py',
        'test_utils/test_utils.py',
        'test_workers/test_vector_worker.py',
        'test_workers/test_database_worker.py'
    ]
    
    for expected_file in expected_files:
        file_path = os.path.join(test_dir, expected_file)
        if os.path.exists(file_path):
            print(f"✓ {expected_file}")
        else:
            print(f"✗ {expected_file} - MISSING")
            issues.append(f"Missing test file: {expected_file}")
    
    # Check if __init__.py files exist
    init_files = [
        '__init__.py',
        'test_utils/__init__.py',
        'test_workers/__init__.py'
    ]
    
    for init_file in init_files:
        file_path = os.path.join(test_dir, init_file)
        if os.path.exists(file_path):
            print(f"✓ {init_file}")
        else:
            print(f"✗ {init_file} - MISSING")
            issues.append(f"Missing init file: {init_file}")
    
    print("="*50)
    
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("All expected test files found!")
        return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description='Run comprehensive unit tests for sc-chatbot-worker'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Run tests with verbose output'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Run tests with coverage analysis'
    )
    parser.add_argument(
        '--pattern',
        default='test*.py',
        help='Test file pattern (default: test*.py)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available test modules'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate test structure'
    )
    
    args = parser.parse_args()
    
    # Add src to Python path
    src_path = os.path.join(os.path.dirname(__file__), 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    print("SC-CHATBOT-WORKER COMPREHENSIVE UNIT TESTS")
    print("="*70)
    
    if args.list:
        list_available_tests()
        return
    
    if args.validate:
        success = validate_test_structure()
        sys.exit(0 if success else 1)
    
    # Set verbosity level
    verbosity = 2 if args.verbose else 1
    
    try:
        if args.coverage:
            success = run_with_coverage()
        else:
            success = run_without_coverage(verbosity, args.pattern)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError running tests: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()