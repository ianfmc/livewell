#!/usr/bin/env python
"""Simple test runner to capture output"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

# Run tests
if __name__ == "__main__":
    from tests.test_strategy_rsi import *
    
    import unittest
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestRSIWilder))
    suite.addTests(loader.loadTestsFromTestCase(TestMACD))
    suite.addTests(loader.loadTestsFromTestCase(TestTrendOk))
    suite.addTests(loader.loadTestsFromTestCase(TestGenerateRSISignals))
    suite.addTests(loader.loadTestsFromTestCase(TestCalculateSignalConfidence))
    suite.addTests(loader.loadTestsFromTestCase(TestApplyGuardrails))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)
    
    sys.exit(0 if result.wasSuccessful() else 1)
