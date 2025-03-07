import unittest


# from conflict_interface.logger_config import setup_library_logger


def run_tests():
    """
    Discover and run all tests in the project.

    This script will:
    - Discover test files starting with 'test_' or ending with '_test.py'
    - Run all discovered tests
    - Provide a detailed test summary
    - Exit with appropriate status code
    """
    # Create test loader to discover tests
    test_loader = unittest.TestLoader()

    # Discover tests in current directory and subdirectories
    test_suite = test_loader.discover(
        start_dir='.',  # Start searching from current directory
        pattern='test_*'  # Find files starting with 'test_'
    )

    # Create test runner with verbosity
    test_runner = unittest.TextTestRunner(verbosity=2)

    # Run the test suite
    test_result = test_runner.run(test_suite)

    # Exit with non-zero code if tests fail
    sys.exit(not test_result.wasSuccessful())


# Run tests if script is executed directly
if __name__ == '__main__':
    # setup_library_logger(logging.DEBUG)
    run_tests()